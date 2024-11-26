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
