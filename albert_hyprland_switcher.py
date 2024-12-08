```python
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2014 Manuel Schneider

from pathlib import Path
from typing import Optional, List
import subprocess
import json
from dataclasses import dataclass
from typing import List, Optional


from albert import *

md_iid = '2.3'
md_version = "1.6"
md_name = "hyprland switcher"
md_description = "hyprland switcher"
md_license = "BSD-3"
md_url = "dong"
md_authors = "@gbdngb12"

@dataclass
class Workspace:
    id: int
    name: str

@dataclass
class HyprlandClient:
    address: str
    # mapped: bool
    # hidden: bool
    # at: List[int]
    # size: List[int]
    workspace: Workspace
    # floating: bool
    # pseudo: bool
    monitor: int
    window_class: str  # "class" 필드는 예약어이므로 변경
    title: str
    # initialClass: str
    # initialTitle: str
    # pid: int
    # xwayland: bool
    # pinned: bool
    # fullscreen: int
    # fullscreenClient: int
    # grouped: List[str]
    # tags: List[str]
    # swallowing: str
    # focusHistoryID: int

    @classmethod
    def from_dict(cls, data: dict):
        # workspace를 먼저 처리
        ws_data = data.get("workspace", {})
        workspace = Workspace(id=ws_data["id"], name=ws_data["name"])

        # HyprlandClient 인스턴스 생성
        return cls(
            address=data["address"],
            # mapped=data["mapped"],
            # hidden=data["hidden"],
            # at=data["at"],
            # size=data["size"],
            workspace=workspace,
            # floating=data["floating"],
            # pseudo=data["pseudo"],
            monitor=data["monitor"],
            window_class=data["class"],
            title=data["title"],
            # initialClass=data["initialClass"],
            # initialTitle=data["initialTitle"],
            # pid=data["pid"],
            # xwayland=data["xwayland"],
            # pinned=data["pinned"],
            # fullscreen=data["fullscreen"],
            # fullscreenClient=data["fullscreenClient"],
            # grouped=data["grouped"],
            # tags=data["tags"],
            # swallowing=data["swallowing"],
            # focusHistoryID=data["focusHistoryID"]
        )

class HyprlandWindowManager:
    def __init__(self):
        pass
    def _run_command(self, command:str) -> Optional[str]:
        try:
            result = subprocess.run(
                command, capture_output=True, shell=True, text=True
            )
            print(f"command : {command}")
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {command}")
            print(f"Error output: {e.stderr}")
            return None
    def get_current_windows(self) -> Optional[List[HyprlandClient]]:
        results:List[HyprlandClient] = []
        hyprland_client_jsons = self._run_command("hyprctl -j clients")
        if hyprland_client_jsons is None:
            return None
        hyprland_client_jsons = json.loads(hyprland_client_jsons)
        for hyprland_client in hyprland_client_jsons:
            results.append(HyprlandClient(hyprland_client["address"],Workspace(hyprland_client["workspace"]["id"], hyprland_client["workspace"]["name"]),hyprland_client["monitor"], hyprland_client["class"],hyprland_client["title"]))
        return results
    def switch_window(self, address:str):
        # hyprctl dispatch focuswindow address:0x6083e13d8620
        self._run_command(f"hyprctl dispatch focuswindow address:{address}")
    
    def move_and_switch_window(self, address:str):
        current_workspace_id = self.get_current_workspace_id()
        self.switch_window(address)
        self._run_command(f"hyprctl dispatch movetoworkspace {current_workspace_id}")
    
    def get_current_workspace_id(self)-> Optional[int]: 
        ret = self._run_command("hyprctl activeworkspace -j | jq '.id'")
        if ret is None:
            return None
        return int(ret)

        


class Plugin(PluginInstance, TriggerQueryHandler):

    def __init__(self):
        PluginInstance.__init__(self)
        TriggerQueryHandler.__init__(
            self, self.id, self.name, self.description,
            defaultTrigger='s '
        )
        self.iconUrls = [f"file:{Path(__file__).parent}/python.svg"]
        self.manager = HyprlandWindowManager()

    def handleTriggerQuery(self, query):
        self.window_list = self.manager.get_current_windows()
        if self.window_list:
            for window in self.window_list:             
                # query.string을 소문자로 변환하여 검색
                search_term = query.string.lower()
                
                # caption 또는 desktops 값과 검색어가 일치하는지 확인
                if search_term in (f"[{window.workspace.id}] +{window.title}").lower() :
                    print(f"FOUND {window}")
                    # window 값을 캡처하여 람다식에서 올바르게 참조
                    current_window_address = window.address
                    query.add(StandardItem(
                        id=self.id,
                        text=f"[{window.workspace.id}] {window.title}",
                        subtext=f"Desktop {window.workspace.id} {window.window_class}",
                        inputActionText=query.trigger + window.title,
                        iconUrls=[f"xdg:{window.window_class}"],
                        actions=[
                            Action(
                                "Switch Window",
                                "Switch Window",
                                lambda id=current_window_address: self.manager.switch_window(id)
                            ),
                            Action(
                                "Move window to this desktop",
                                "Move window to this desktop",
                                lambda id=current_window_address: self.manager.move_and_switch_window(id)
                            ),
                            # Action(
                            #     "Close the window gracefully",
                            #     "Close the window gracefully",
                            #     lambda id=current_window_address: self.manager.run_script(ScriptMode.CLOSE_WINDOW, id)
                            # )
                        ]
                    ))
```
