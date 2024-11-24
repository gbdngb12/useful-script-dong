# -*- coding: utf-8 -*-
# Copyright (c) 2017-2014 Manuel Schneider

from builtins import pow
from math import *
from pathlib import Path

from albert import *

md_iid = "2.3"
md_version = "3.0"
md_name = "Wireguard"
md_description = "Control Wireguard"
md_license = "BSD-3"
md_url = "None"
md_authors = "@gbdngb12"


class Plugin(PluginInstance, TriggerQueryHandler):

    def __init__(self):
        PluginInstance.__init__(self)
        TriggerQueryHandler.__init__(
            self, self.id, self.name, self.description,
            synopsis='<toggle>',
            defaultTrigger='wr '
        )
        self.iconUrls = [f"file:{Path(__file__).parent}/wireguard.png"]

    def handleTriggerQuery(self, query):
        peer = "peer4"
        query.add(StandardItem(
            id=self.id,
            text=peer,
            subtext=type(peer).__name__,
            inputActionText=query.trigger + peer,
            iconUrls=self.iconUrls,
            actions = [
                Action("exe", "Toggle Wireguard", lambda: runTerminal("wg-quick up peer4")),
                Action("exe", "Disable Wireguard", lambda: runTerminal("wg-quick down peer4")),
            ]
        ))
