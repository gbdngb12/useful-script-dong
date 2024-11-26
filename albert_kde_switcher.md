# 목표
- [ ] wayland, x11 windows switch 통합 in KDE
- [ ] firefox tabs도 switch가능하도록(krunner 코드 참조)
# 1. Get windows list
```js
try {
 // console.log(Object.keys(workspace));
var clients = workspace.windowList();
clients.forEach(client => {
    console.log(`Window Title: ${client.caption}`);
});
} catch (e) {
    console.log(`BUG: ${e.message}`);
}

```

# 2. switch.sh
```bash
#!/bin/bash
# Usage: ww -f "window class filter" -c "run if not found"
# Usage: ww -fa "window title filter" -c "run if not found"

TOGGLE="false"
POSITIONAL=()
while [[ $# -gt 0 ]]; do
        key="$1"

        case $key in
        -c | --command)
                COMMAND="$2"
                shift # past argument
                shift # past value
                ;;
        -f | --filter)
                FILTERBY="$2"
                shift # past argument
                shift # past value
                ;;
        -fa | --filter-alternative)
                FILTERALT="$2"
                shift # past argument
                shift # past value
                ;;
        -t | --toggle)
                TOGGLE="true"
                shift # past argument
                ;;
        -h | --help)
                HELP="1"
                shift # past argument
                shift # past value
                ;;
        *)                  # unknown option
                POSITIONAL+=("$1") # save it in an array for later
                shift              # past argument
                ;;
        esac
done

set -- "${POSITIONAL[@]}" # restore positional parameters

if [ -n "$HELP" ]; then
        cat <<EOF
ww. Utility to raise or jump an applications in KDE. It interacts with KWin using KWin scripts and it is compatible with X11 and Wayland

Paramaters:

-h  --help                show this help
-f  --filter              filter by window class
-fa --filter-alternative  filter by window title (caption)
-t  --toggle              also minimize the window if it is already active
-c  --command             command to check if running and run if no process is found
EOF
        exit 0
fi

SCRIPT_TEMPLATE=$(
        cat <<EOF
function kwinactivateclient(clientClass, clientCaption, toggle) {
  var clients = workspace.stackingOrder;
  var compareToCaption = new RegExp(clientCaption || '', 'i');
  var compareToClass = clientClass;
  var isCompareToClass = clientClass.length > 0
  for (var i=0; i<clients.length; i++) {
      var client = clients[i];
      var classCompare = (isCompareToClass && client.resourceClass == compareToClass);
      var captionCompare = (!isCompareToClass && compareToCaption.exec(client.caption));
      if (classCompare || captionCompare) {
          if (workspace.activeWindow != client) {
              workspace.activeWindow = client;
          } else if (toggle) {
              client.minimized = true;
          }
          break;
      }
  }
}
kwinactivateclient('CLASS_NAME', 'CAPTION_NAME', TOGGLE);
EOF
)

CURRENT_SCRIPT_NAME=$(basename "$0")

# ensure the script file exists
function ensure_script {
        if [ ! -f SCRIPT_PATH ]; then
                if [ ! -d "$SCRIPT_FOLDER" ]; then
                        mkdir -p "$SCRIPT_FOLDER"
                fi
                SCRIPT_CONTENT=${SCRIPT_TEMPLATE/CLASS_NAME/$1}
                SCRIPT_CONTENT=${SCRIPT_CONTENT/CAPTION_NAME/$2}
                SCRIPT_CONTENT=${SCRIPT_CONTENT/TOGGLE/$3}
                #if [ "$1" == "class" ]; then
                #SCRIPT_CONTENT=${SCRIPT_CLASS_NAME/REPLACE_ME/$2}
                #else
                #SCRIPT_CONTENT=${SCRIPT_CAPTION/REPLACE_ME/$2}
                #fi
                echo "$SCRIPT_CONTENT" >"$SCRIPT_PATH"
        fi
}

if [ -z "$FILTERBY" ] && [ -z "$FILTERALT" ]; then
        echo You need to specify a window filter. Either by class -f or by title -fa
        exit 1
fi

IS_RUNNING=$(pgrep -o -a -f "$COMMAND" | grep -v "$CURRENT_SCRIPT_NAME")

if [ -n "$IS_RUNNING" ] || [ -n "$FILTERALT" ]; then

        # trying for XDG_CONFIG_HOME first
        SCRIPT_FOLDER_ROOT=$XDG_CONFIG_HOME
        if [[ -z $SCRIPT_FOLDER_ROOT ]]; then
                # fallback to the home folder
                SCRIPT_FOLDER_ROOT=$HOME
        fi

        SCRIPT_FOLDER="$SCRIPT_FOLDER_ROOT/.wwscripts/"
        SCRIPT_NAME=$(echo "$FILTERBY$FILTERALT" | md5sum | head -c 32)
        SCRIPT_PATH="$SCRIPT_FOLDER$SCRIPT_NAME"
        ensure_script "$FILTERBY" "$FILTERALT" "$TOGGLE"

        SCRIPT_NAME="ww$RANDOM"
        #SCRIPT_NAME=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)

        # install the script
        ID=$(dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting org.kde.kwin.Scripting.loadScript "string:$SCRIPT_PATH" "string:$SCRIPT_NAME" | awk '{print $2}') >/dev/null 2>&1
        # run it
        dbus-send --session --dest=org.kde.KWin --print-reply=literal "/Scripting/Script$ID" org.kde.kwin.Script.run >/dev/null 2>&1
        # stop it
        dbus-send --session --dest=org.kde.KWin --print-reply=literal "/Scripting/Script$ID" org.kde.kwin.Script.stop >/dev/null 2>&1
        # uninstall it
        dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting org.kde.kwin.Scripting.unloadScript "string:$SCRIPT_NAME" >/dev/null 2>&1
elif [ -n "$COMMAND" ]; then
        $COMMAND &
fi
```


```python
import os
import hashlib
import subprocess
from enum import Enum
import json
from datetime import datetime

class ScriptMode(Enum):
    GET_WINDOW_LIST = 1
    SET_WINDOW = 2

class KWinScriptManager:
    def __init__(self):
        self.script_folder_root = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~"))
        self.script_folder = os.path.join(self.script_folder_root, ".wwscripts/")
        self.datetime_now = None

    def _run_command(self, command, capture_output=True):
        """Helper method to run a shell command."""
        try:
            result = subprocess.run(
                command, capture_output=capture_output, shell=True, text=True, check=True
            )
            return result.stdout.strip() if capture_output else None
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {command}")
            print(f"Error output: {e.stderr}")
            return None

    def _generate_script_content(self, mode: ScriptMode, target_caption=None):
        """Generate the script content based on the mode."""
        if mode == ScriptMode.GET_WINDOW_LIST:
            return """
            var clients = workspace.windowList();
            var clientData = [];
            clients.forEach(client => {
                var name = client.caption;
                if (name.length > 0) {
                    clientData.push({
                        desktops: client.desktops[0].x11DesktopNumber,
                        icon: client.resourceClass,
                        caption: client.caption
                    });
                }
            });
            console.log(JSON.stringify(clientData, null, 2));
            """
        elif mode == ScriptMode.SET_WINDOW:
            if not target_caption:
                raise ValueError("Target caption must be set for SET_WINDOW mode.")
            return f"""
            var target = "{target_caption}";
            var clients = workspace.windowList();
            for (const client of clients) {{
                var name = client.caption;
                if (name && name.includes(target)) {{
                    workspace.activeWindow = client;
                    break;
                }}
            }}
            """
        else:
            raise ValueError("Invalid script mode.")

    def _generate_script_path(self, mode: ScriptMode, target_caption=None):
        """Ensure the script exists and return its path."""
        script_content = self._generate_script_content(mode, target_caption)
        script_name = hashlib.md5((target_caption or str(mode)).encode()).hexdigest()
        script_path = os.path.join(self.script_folder, script_name)

        if not os.path.isfile(script_path):
            os.makedirs(self.script_folder, exist_ok=True)
            with open(script_path, "w") as script_file:
                script_file.write(script_content)

        return script_path

    def _fetch_logs(self):
        """Fetch logs from KWin."""
        command = f'journalctl _COMM=kwin_wayland -o cat --since "{self.datetime_now}"'
        logs = self._run_command(command, True)
        if logs:
            log_output = logs.rstrip().split("\n")
            log_output = [line.lstrip("js: ") for line in log_output]
            return json.loads("\n".join(log_output))
        return []

    def run_script(self, mode: ScriptMode, target_caption=None):
        """Run the script with the KWin D-Bus interface."""
        script_path = self._generate_script_path(mode, target_caption)
        script_name = f"ww{os.urandom(4).hex()}"
        dbus_load = f"dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting org.kde.kwin.Scripting.loadScript string:{script_path} string:{script_name}"
        dbus_run = f"dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting/Script{{ID}} org.kde.kwin.Script.run"
        dbus_stop = f"dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting/Script{{ID}} org.kde.kwin.Script.stop"
        dbus_unload = f"dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting org.kde.kwin.Scripting.unloadScript string:{script_name}"

        try:
            self.datetime_now = datetime.now().isoformat()
            result = self._run_command(dbus_load)
            if not result:
                print("Failed to load the script.")
                return None

            script_id = result.strip().split()[-1]
            
            self._run_command(dbus_run.format(ID=script_id))

            self._run_command(dbus_stop.format(ID=script_id))
            self._run_command(dbus_unload)

            if mode == ScriptMode.GET_WINDOW_LIST:
                return self._fetch_logs()
            os.remove(script_path)
        except Exception as e:
            print(f"Error running script: {e}")
            return None


# Example usage
if __name__ == "__main__":
    target_caption = "IDA - 04_mstscax.dll.i64 (04_mstscax.dll) /home/dong/Develop/poc/04_mstscax.dll.i64"
    manager = KWinScriptManager()

    # Set a specific window
    # result = manager.run_script(ScriptMode.SET_WINDOW, target_caption)

    # Or, get the window list
    result = manager.run_script(ScriptMode.GET_WINDOW_LIST)

    if result:
        print(result)
    else:
        print("No result returned.")
```

## version 1
```python
import subprocess
from datetime import datetime
import os
import hashlib
from enum import Enum
from typing import Optional, List
import json

class ScriptMode(Enum):
    GET_WINDOW_LIST = 1
    SET_WINDOW = 2
    
class KWinScriptManager:
    def __init__(self):
        self.script_folder_root = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~"))
        self.script_folder = os.path.join(self.script_folder_root, ".wwscripts/")
    
    def _run_command(self, command:str) -> Optional[str]:
        try:
            result = subprocess.run(
                command, capture_output=True, shell=True, text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {command}")
            print(f"Error output: {e.stderr}")
            return None
    
    def _fetch_log(self, datetime_start):
        since = str(datetime_start)
        return json.loads('\n'.join([el.lstrip("js: ") for el in self._run_command("journalctl _COMM=kwin_wayland -o cat --since \"" + since + "\"").rstrip().split("\n")]))
        
    
    def _generate_script(self, mode:ScriptMode, target_id: Optional[str]):
        if mode == ScriptMode.GET_WINDOW_LIST:
            return """
            var clients = workspace.windowList();
            var clientData = [];
            clients.forEach(client => {
                var name = client.caption;
                if (name.length > 0) {
                    clientData.push({
                        desktops: client.desktops[0].x11DesktopNumber,
                        icon: client.resourceClass,
                        caption: client.caption,
                        id: client.internalId
                    });
                }
            });
            console.log(JSON.stringify(clientData, null, 2));
            """
        elif mode == ScriptMode.SET_WINDOW:
            if not target_id:
                raise ValueError("Target caption must be set for SET_WINDOW mode.")
            return f"""
            var target_id = "{target_id}";
            var clients = workspace.windowList();
            for (const client of clients) {{
                if (target_id == String(client.internalId)) {{
                    workspace.activeWindow = client;
                    break;
                }}
            }}
            """
        else:
            raise ValueError("Invalid script mode.")
    
    def run_script(self, mode:ScriptMode, target_id:Optional[str]) -> Optional[List]:
        datetime_now = datetime.now()
        # 0. save Script
        self.script_name = hashlib.md5(str(mode).encode()).hexdigest()
        self.script_path = os.path.join(self.script_folder, self.script_name)
        with open(self.script_path, 'w') as file:
            file.write(self._generate_script(mode, target_id))
        
        # 1. load
        result = self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting org.kde.kwin.Scripting.loadScript \"string:{self.script_path}\" \"string:{self.script_name}\"")
        if not result:
            raise Exception("SCRIPT INSTALL ERROR")
        script_id = result.strip().split()[-1]
        
        # 2. run
        self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal \"/Scripting/Script{script_id}\" org.kde.kwin.Script.run")
        # 3. stop
        self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal \"/Scripting/Script{script_id}\" org.kde.kwin.Script.stop")
        # 4. uninstall
        self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting org.kde.kwin.Scripting.unloadScript \"string:{self.script_name}\"")
        if mode == ScriptMode.GET_WINDOW_LIST:
            return self._fetch_log(datetime_now)

        # 5. remove Script
        os.remove(self.script_path)
    
        

manager = KWinScriptManager()
target_id = "{adabc5cf-6d77-406d-be27-6ca8e6fd67fd}"
print(manager.run_script(ScriptMode.SET_WINDOW ,target_id))

```

## Albert Version
```python
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2014 Manuel Schneider

from pathlib import Path
import subprocess
from datetime import datetime
import os
import hashlib
from enum import Enum
from typing import Optional, List
import json

from albert import *

md_iid = '2.3'
md_version = "1.6"
md_name = "kde switcher"
md_description = "kde switcher"
md_license = "BSD-3"
md_url = "dong"
md_authors = "@gbdngb12"


class ScriptMode(Enum):
    GET_WINDOW_LIST = 1
    SET_WINDOW = 2
    
class KWinScriptManager:
    def __init__(self):
        self.script_folder_root = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~"))
        self.script_folder = os.path.join(self.script_folder_root, ".wwscripts/")
    
    def _run_command(self, command:str) -> Optional[str]:
        try:
            result = subprocess.run(
                command, capture_output=True, shell=True, text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {command}")
            print(f"Error output: {e.stderr}")
            return None
    
    def _fetch_log(self, datetime_start):
        since = str(datetime_start)
        return json.loads('\n'.join([el.lstrip("js: ") for el in self._run_command("journalctl _COMM=kwin_wayland -o cat --since \"" + since + "\"").rstrip().split("\n")]))
        
    
    def _generate_script(self, mode:ScriptMode, target_id: Optional[str]):
        if mode == ScriptMode.GET_WINDOW_LIST:
            return """
            var clients = workspace.windowList();
            var clientData = [];
            clients.forEach(client => {
                var name = client.caption;
                if (name.length > 0) {
                    clientData.push({
                        desktops: client.desktops[0].x11DesktopNumber,
                        icon: client.resourceClass,
                        caption: client.caption,
                        id: client.internalId
                    });
                }
            });
            console.log(JSON.stringify(clientData, null, 2));
            """
        elif mode == ScriptMode.SET_WINDOW:
            if not target_id:
                raise ValueError("Target caption must be set for SET_WINDOW mode.")
            return f"""
            var target_id = "{target_id}";
            var clients = workspace.windowList();
            for (const client of clients) {{
                if (target_id == String(client.internalId)) {{
                    workspace.activeWindow = client;
                    break;
                }}
            }}
            """
        else:
            raise ValueError("Invalid script mode.")
    
    def run_script(self, mode:ScriptMode, target_id:Optional[str]) -> Optional[List]:
        datetime_now = datetime.now()
        # 0. save Script
        self.script_name = hashlib.md5(str(mode).encode()).hexdigest()
        self.script_path = os.path.join(self.script_folder, self.script_name)
        print(f"target_id : {target_id}")
        with open(self.script_path, 'w') as file:
            file.write(self._generate_script(mode, target_id))
        
        # 1. load
        result = self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting org.kde.kwin.Scripting.loadScript \"string:{self.script_path}\" \"string:{self.script_name}\"")
        if not result:
            raise Exception("SCRIPT INSTALL ERROR")
        script_id = result.strip().split()[-1]
        
        # 2. run
        self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal \"/Scripting/Script{script_id}\" org.kde.kwin.Script.run")
        # 3. stop
        self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal \"/Scripting/Script{script_id}\" org.kde.kwin.Script.stop")
        # 4. uninstall
        self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting org.kde.kwin.Scripting.unloadScript \"string:{self.script_name}\"")
        if mode == ScriptMode.GET_WINDOW_LIST:
            return self._fetch_log(datetime_now)
        else:
            print("i am set window")
        # 5. remove Script
        os.remove(self.script_path)

class Plugin(PluginInstance, TriggerQueryHandler):

    def __init__(self):
        PluginInstance.__init__(self)
        TriggerQueryHandler.__init__(
            self, self.id, self.name, self.description,
            defaultTrigger='wm '
        )
        print("kde init")
        self.iconUrls = [f"file:{Path(__file__).parent}/python.svg"]
        self.manager = KWinScriptManager()

    def handleTriggerQuery(self, query):
        self.window_list= self.manager.run_script(ScriptMode.GET_WINDOW_LIST, None)
        if self.window_list:
            for window in self.window_list:
                print(window)
                if query.string in window['caption']:
                    print(f"FOUND {window}")
                    # window 값을 캡처하여 람다식에서 올바르게 참조
                    current_window_id = window['id']
                    query.add(StandardItem(
                        id=self.id,
                        text=f"[{window['desktops']}] {window['caption']}",
                        subtext=window['id'],
                        inputActionText=query.trigger + window['caption'],
                        iconUrls=[f"xdg:{window['icon']}"],
                        actions=[
                            Action(
                                "Switch Window",
                                "Switch Window",
                                lambda id=current_window_id: self.manager.run_script(ScriptMode.SET_WINDOW, id)
                            )
                        ]
                    ))
```

## albert version2

```python
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2014 Manuel Schneider

from pathlib import Path
import subprocess
from datetime import datetime
import os
import hashlib
from enum import Enum
from typing import Optional, List
import json


from albert import *

md_iid = '2.3'
md_version = "1.6"
md_name = "kde switcher"
md_description = "kde switcher"
md_license = "BSD-3"
md_url = "dong"
md_authors = "@gbdngb12"


class ScriptMode(Enum):
    GET_WINDOW_LIST = 1
    SET_WINDOW = 2
    
class KWinScriptManager:
    def __init__(self):
        self.script_folder_root = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~"))
        self.script_folder = os.path.join(self.script_folder_root, ".wwscripts/")
    
    def _run_command(self, command:str) -> Optional[str]:
        try:
            result = subprocess.run(
                command, capture_output=True, shell=True, text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {command}")
            print(f"Error output: {e.stderr}")
            return None
    
    def _fetch_log(self, datetime_start):
        since = str(datetime_start)
        return json.loads('\n'.join([el.lstrip("js: ") for el in self._run_command("journalctl _COMM=kwin_wayland -o cat --since \"" + since + "\"").rstrip().split("\n")]))
        
    
    def _generate_script(self, mode:ScriptMode, target_id: Optional[str]):
        if mode == ScriptMode.GET_WINDOW_LIST:
            return """
            var clients = workspace.windowList();
            var clientData = [];
            clients.forEach(client => {
                var name = client.caption;
                if (name.length > 0) {
                    clientData.push({
                        desktops: client.desktops[0].x11DesktopNumber,
                        icon: client.resourceClass,
                        caption: client.caption,
                        id: client.internalId
                    });
                }
            });
            console.log(JSON.stringify(clientData, null, 2));
            """
        elif mode == ScriptMode.SET_WINDOW:
            if not target_id:
                raise ValueError("Target caption must be set for SET_WINDOW mode.")
            return f"""
            var target_id = "{target_id}";
            var clients = workspace.windowList();
            for (const client of clients) {{
                if (target_id == String(client.internalId)) {{
                    workspace.activeWindow = client;
                    break;
                }}
            }}
            """
        else:
            raise ValueError("Invalid script mode.")
    
    def run_script(self, mode:ScriptMode, target_id:Optional[str]) -> Optional[List]:
        datetime_now = datetime.now()
        # 0. save Script
        self.script_name = hashlib.md5(str(mode).encode()).hexdigest()
        self.script_path = os.path.join(self.script_folder, self.script_name)
        print(f"target_id : {target_id}")
        with open(self.script_path, 'w') as file:
            file.write(self._generate_script(mode, target_id))
        
        # 1. load
        result = self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting org.kde.kwin.Scripting.loadScript \"string:{self.script_path}\" \"string:{self.script_name}\"")
        if not result:
            raise Exception("SCRIPT INSTALL ERROR")
        script_id = result.strip().split()[-1]
        
        # 2. run
        self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal \"/Scripting/Script{script_id}\" org.kde.kwin.Script.run")
        # 3. stop
        self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal \"/Scripting/Script{script_id}\" org.kde.kwin.Script.stop")
        # 4. uninstall
        self._run_command(f"dbus-send --session --dest=org.kde.KWin --print-reply=literal /Scripting org.kde.kwin.Scripting.unloadScript \"string:{self.script_name}\"")
        if mode == ScriptMode.GET_WINDOW_LIST:
            return self._fetch_log(datetime_now)
        else:
            print("i am set window")
        # 5. remove Script
        os.remove(self.script_path)

class Plugin(PluginInstance, TriggerQueryHandler):

    def __init__(self):
        PluginInstance.__init__(self)
        TriggerQueryHandler.__init__(
            self, self.id, self.name, self.description,
            defaultTrigger='s '
        )
        print("kde init")
        self.iconUrls = [f"file:{Path(__file__).parent}/python.svg"]
        self.manager = KWinScriptManager()

    def handleTriggerQuery(self, query):
        self.window_list = self.manager.run_script(ScriptMode.GET_WINDOW_LIST, None)
        if self.window_list:
            for window in self.window_list:
                print(window)
                
                # query.string을 소문자로 변환하여 검색
                search_term = query.string.lower()
                
                # caption 또는 desktops 값과 검색어가 일치하는지 확인
                if search_term in (f"[{window['desktops']}] +{window['caption']}").lower():
                    print(f"FOUND {window}")
                    # window 값을 캡처하여 람다식에서 올바르게 참조
                    current_window_id = window['id']
                    query.add(StandardItem(
                        id=self.id,
                        text=f"[{window['desktops']}] {window['caption']}",
                        subtext=f"Desktop {window['desktops']} {window['icon']}",
                        inputActionText=query.trigger + window['caption'],
                        iconUrls=[f"xdg:{window['icon']}", window['icon']],
                        actions=[
                            Action(
                                "Switch Window",
                                "Switch Window",
                                lambda id=current_window_id: self.manager.run_script(ScriptMode.SET_WINDOW, id)
                            )
                        ]
                    ))
```
