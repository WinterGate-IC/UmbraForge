"""Compact SVG source table for the icon browser.

Coordinates are arbitrary; :func:`umbraforge.geometry._svg` normalizes every
drawing into the unit square. The fourth value in each row is the stroke width
in unit space, or 0 for a filled silhouette.

Keeping the data separate from the drawing helpers makes the shelf easy to
extend: add a row, restart, and the icon appears in the browser, inspector and
renderer with no other wiring.
"""

from __future__ import annotations

ICON_SVG: tuple[tuple[str, str, str, float, str], ...] = (
    # interface ---------------------------------------------------------
    ("check", "Check", "M3 12 L9 18 L21 5", 0.10, "UI"),
    ("close", "Close", "M5 5 L19 19 M19 5 L5 19", 0.10, "UI"),
    ("plus", "Plus", "M12 4 L12 20 M4 12 L20 12", 0.10, "UI"),
    ("minus", "Minus", "M4 10 L20 10 L20 14 L4 14 Z", 0.0, "UI"),
    ("menu", "Menu", "M4 6 L20 6 M4 12 L20 12 M4 18 L20 18", 0.09, "UI"),
    ("home", "Home", "M3 11 L12 3 L21 11 M6 9 L6 21 L18 21 L18 9 "
     "M10 21 L10 14 L14 14 L14 21", 0.08, "UI"),
    ("search", "Search", "M3 10 A7 7 0 0 1 17 10 A7 7 0 0 1 3 10 "
     "M15.5 15.5 L21 21", 0.09, "UI"),
    ("trash", "Trash", "M4 7 L20 7 M9 7 L9 4 L15 4 L15 7 M6 7 L7 21 "
     "L17 21 L18 7 M10 11 L10 18 M14 11 L14 18", 0.08, "UI"),
    ("edit", "Edit", "M4 20 L4 16 L16 4 L20 8 L8 20 Z M13 7 L17 11", 0.07,
     "UI"),
    ("copy", "Copy", "M8 8 L20 8 L20 20 L8 20 Z M4 16 L4 4 L16 4", 0.08,
     "UI"),
    ("download", "Download", "M12 3 L12 15 M7 10 L12 15 L17 10 "
     "M4 20 L20 20", 0.09, "UI"),
    ("upload", "Upload", "M12 16 L12 4 M7 9 L12 4 L17 9 M4 20 L20 20", 0.09,
     "UI"),
    ("refresh", "Refresh", "M4 12 A8 8 0 0 1 19 7 M19 3 L19 7 L15 7 "
     "M20 12 A8 8 0 0 1 5 17 M5 21 L5 17 L9 17", 0.08, "UI"),
    ("link", "Link", "M9 15 L15 9 M7 11 L5 13 A3 3 0 0 0 9 17 L11 15 "
     "M13 9 L15 7 A3 3 0 0 1 19 11 L17 13", 0.08, "UI"),
    ("lock", "Lock", "M6 11 L18 11 L18 21 L6 21 Z M9 11 L9 8 A3 3 0 0 1 "
     "15 8 L15 11", 0.08, "UI"),
    ("unlock", "Unlock", "M6 11 L18 11 L18 21 L6 21 Z M9 11 L9 8 "
     "A3 3 0 0 1 15 8", 0.08, "UI"),
    ("key", "Key", "M3 12 A4 4 0 0 1 11 12 A4 4 0 0 1 3 12 M11 12 L21 12 "
     "M17 12 L17 15 M20 12 L20 14", 0.08, "UI"),
    ("bell", "Bell", "M6 17 L6 11 A6 6 0 0 1 18 11 L18 17 L20 19 L4 19 Z "
     "M10 21 L14 21", 0.07, "UI"),
    ("calendar", "Calendar", "M4 6 L20 6 L20 21 L4 21 Z M4 10 L20 10 "
     "M8 3 L8 7 M16 3 L16 7", 0.08, "UI"),
    ("clock", "Clock", "M3 12 A9 9 0 0 1 21 12 A9 9 0 0 1 3 12 "
     "M12 6 L12 12 L16 15", 0.08, "UI"),
    ("image", "Image", "M3 4 L21 4 L21 20 L3 20 Z M7 9 A1.5 1.5 0 0 1 7 12 "
     "A1.5 1.5 0 0 1 7 9 M3 17 L8 12 L12 16 L16 11 L21 16", 0.07, "UI"),
    ("folder", "Folder", "M3 6 L10 6 L12 9 L21 9 L21 20 L3 20 Z", 0.08,
     "UI"),
    ("file", "File", "M6 3 L15 3 L20 8 L20 21 L6 21 Z M15 3 L15 8 L20 8",
     0.08, "UI"),
    ("save", "Save", "M4 3 L17 3 L21 7 L21 21 L3 21 Z M7 3 L7 9 L16 9 "
     "L16 3 M7 14 L17 14 L17 21 L7 21 Z", 0.07, "UI"),
    ("print", "Print", "M6 3 L18 3 L18 8 L6 8 Z M3 8 L21 8 L21 17 L18 17 "
     "L18 21 L6 21 L6 17 L3 17 Z", 0.07, "UI"),
    ("filter", "Filter", "M3 4 L21 4 L14 13 L14 21 L10 18 L10 13 Z", 0.07,
     "UI"),
    ("list", "List", "M4 6 L6 6 M9 6 L21 6 M4 12 L6 12 M9 12 L21 12 "
     "M4 18 L6 18 M9 18 L21 18", 0.10, "UI"),
    ("grid", "Grid", "M3 3 L10 3 L10 10 L3 10 Z M14 3 L21 3 L21 10 L14 10 Z "
     "M3 14 L10 14 L10 21 L3 21 Z M14 14 L21 14 L21 21 L14 21 Z", 0.06,
     "UI"),
    ("pin", "Pin", "M12 2 A6 6 0 0 1 18 8 C18 14 12 22 12 22 C12 22 6 14 "
     "6 8 A6 6 0 0 1 12 2 Z M12 5 A3 3 0 0 1 12 11 A3 3 0 0 1 12 5", 0.07,
     "UI"),
    ("bookmark", "Bookmark", "M6 3 L18 3 L18 21 L12 16 L6 21 Z", 0.07,
     "UI"),
    ("tag", "Tag", "M3 3 L12 3 L21 12 L12 21 L3 12 Z M7 7 L9 9", 0.07,
     "UI"),
    ("play", "Play", "M6 3 L21 12 L6 21 Z", 0.0, "UI"),
    ("pause", "Pause", "M6 4 L10 4 L10 20 L6 20 Z M14 4 L18 4 L18 20 L14 20 Z",
     0.0, "UI"),
    ("stop", "Stop", "M5 5 L19 5 L19 19 L5 19 Z", 0.0, "UI"),
    ("rewind", "Rewind", "M11 5 L2 12 L11 19 Z M22 5 L13 12 L22 19 Z", 0.0,
     "UI"),
    ("forward", "Fast forward", "M2 5 L11 12 L2 19 Z M13 5 L22 12 L13 19 Z",
     0.0, "UI"),
    ("volume", "Volume", "M3 9 L8 9 L13 4 L13 20 L8 15 L3 15 Z "
     "M16 9 A4 4 0 0 1 16 15 M18 6 A8 8 0 0 1 18 18", 0.07, "UI"),
    ("mute", "Mute", "M3 9 L8 9 L13 4 L13 20 L8 15 L3 15 Z M16 9 L22 15 "
     "M22 9 L16 15", 0.07, "UI"),
    ("mic", "Microphone", "M9 3 A3 3 0 0 1 15 3 L15 12 A3 3 0 0 1 9 12 Z "
     "M5 11 A7 7 0 0 0 19 11 M12 18 L12 22 M8 22 L16 22", 0.07, "UI"),
    ("camera", "Camera", "M3 7 L8 7 L10 4 L14 4 L16 7 L21 7 L21 20 L3 20 Z "
     "M12 9 A4 4 0 0 1 12 17 A4 4 0 0 1 12 9", 0.07, "UI"),
    ("video", "Video", "M3 6 L15 6 L15 18 L3 18 Z M15 10 L21 7 L21 17 "
     "L15 14 Z", 0.07, "UI"),
    # people ------------------------------------------------------------
    ("user", "User", "M12 3 A4 4 0 0 1 12 11 A4 4 0 0 1 12 3 "
     "M4 21 A8 8 0 0 1 20 21", 0.08, "People"),
    ("users", "Users", "M9 3 A4 4 0 0 1 9 11 A4 4 0 0 1 9 3 "
     "M2 21 A7 7 0 0 1 16 21 M16 4 A3 3 0 0 1 16 10 M17 14 "
     "A6 6 0 0 1 22 20", 0.07, "People"),
    ("user_plus", "Add user", "M9 3 A4 4 0 0 1 9 11 A4 4 0 0 1 9 3 "
     "M2 21 A7 7 0 0 1 16 21 M19 8 L19 16 M15 12 L23 12", 0.07, "People"),
    ("log_in", "Sign in", "M3 4 L13 4 L13 20 L3 20 Z M13 12 L22 12 "
     "M18 8 L22 12 L18 16", 0.08, "People"),
    ("log_out", "Sign out", "M11 4 L21 4 L21 20 L11 20 Z M3 12 L11 12 "
     "M7 8 L3 12 L7 16", 0.08, "People"),
    # communication ----------------------------------------------------
    ("mail", "Mail", "M3 5 L21 5 L21 19 L3 19 Z M3 6 L12 13 L21 6", 0.08,
     "Communication"),
    ("phone", "Phone", "M5 3 L9 3 L11 8 L8 10 A10 10 0 0 0 14 16 L16 13 "
     "L21 15 L21 19 A2 2 0 0 1 19 21 A16 16 0 0 1 3 5 A2 2 0 0 1 5 3 Z",
     0.07, "Communication"),
    ("at", "At sign", "M12 7 A5 5 0 0 1 17 12 L17 15 A2 2 0 0 0 21 15 "
     "L21 12 A9 9 0 0 0 3 12 A9 9 0 0 0 21 12 M12 7 A5 5 0 0 0 12 17",
     0.07, "Communication"),
    ("hash", "Hash", "M9 3 L7 21 M17 3 L15 21 M4 9 L20 9 M3 15 L19 15",
     0.08, "Communication"),
    ("percent", "Percent", "M5 5 A2 2 0 0 1 5 9 A2 2 0 0 1 5 5 "
     "M19 15 A2 2 0 0 1 19 19 A2 2 0 0 1 19 15 M4 20 L20 4", 0.08,
     "Communication"),
    ("ampersand", "Ampersand", "M9 7 A3 3 0 0 1 15 7 C15 11 7 13 7 17 "
     "A4 4 0 0 0 15 17 C17 15 19 12 21 10 M14 13 L21 21", 0.07,
     "Communication"),
    ("send", "Send", "M3 11 L21 3 L14 21 L11 13 Z M11 13 L21 3", 0.08,
     "Communication"),
    ("chat", "Chat", "M3 4 L21 4 L21 17 L8 17 L3 21 Z M7 9 L17 9 "
     "M7 13 L13 13", 0.08, "Communication"),
    # technology -------------------------------------------------------
    ("cpu", "Processor", "M7 7 L17 7 L17 17 L7 17 Z M10 10 L14 10 L14 14 "
     "L10 14 Z M9 3 L9 7 M15 3 L15 7 M9 17 L9 21 M15 17 L15 21 M3 9 L7 9 "
     "M3 15 L7 15 M17 9 L21 9 M17 15 L21 15", 0.06, "Tech"),
    ("monitor", "Monitor", "M3 4 L21 4 L21 17 L3 17 Z M8 21 L16 21 "
     "M12 17 L12 21", 0.08, "Tech"),
    ("keyboard", "Keyboard", "M3 7 L21 7 L21 17 L3 17 Z M6 10 L6 11 "
     "M9 10 L9 11 M12 10 L12 11 M15 10 L15 11 M18 10 L18 11 "
     "M7 14 L17 14", 0.08, "Tech"),
    ("mouse", "Mouse", "M8 3 A4 4 0 0 1 16 3 L16 15 A4 4 0 0 1 8 15 Z "
     "M12 3 L12 8", 0.07, "Tech"),
    ("laptop", "Laptop", "M4 5 L20 5 L20 16 L4 16 Z M2 19 L22 19 L20 16 "
     "L4 16 Z", 0.07, "Tech"),
    ("server", "Server", "M3 4 L21 4 L21 10 L3 10 Z M3 14 L21 14 L21 20 "
     "L3 20 Z M6 7 L7 7 M6 17 L7 17", 0.08, "Tech"),
    ("database", "Database", "M4 6 A8 3 0 0 1 20 6 A8 3 0 0 1 4 6 L4 18 "
     "A8 3 0 0 0 20 18 L20 6 M4 12 A8 3 0 0 0 20 12", 0.07, "Tech"),
    ("code", "Code", "M8 6 L3 12 L8 18 M16 6 L21 12 L16 18 M13 4 L11 20",
     0.09, "Tech"),
    ("terminal", "Terminal", "M3 4 L21 4 L21 20 L3 20 Z M6 9 L9 12 L6 15 "
     "M12 15 L17 15", 0.08, "Tech"),
    ("bug", "Bug", "M8 7 A4 4 0 0 1 16 7 L16 14 A4 4 0 0 1 8 14 Z "
     "M8 10 L4 10 M8 14 L4 17 M16 10 L20 10 M16 14 L20 17 M9 4 L7 2 "
     "M15 4 L17 2", 0.07, "Tech"),
    ("fingerprint", "Fingerprint", "M6 17 A8 8 0 0 1 18 17 "
     "M8 17 A6 6 0 0 1 16 17 M10 17 A4 4 0 0 1 14 17 "
     "M12 6 A9 9 0 0 0 4 15 M20 15 A9 9 0 0 0 17 7", 0.07, "Tech"),
    ("rocket", "Rocket", "M12 2 C16 6 17 11 15 16 L9 16 C7 11 8 6 12 2 Z "
     "M9 16 L7 21 L12 19 L17 21 L15 16 M12 8 A2 2 0 0 1 12 12 "
     "A2 2 0 0 1 12 8", 0.07, "Tech"),
    ("satellite", "Satellite", "M12 8 L16 4 L20 8 L16 12 Z M8 12 L12 16 "
     "L8 20 L4 16 Z M10 10 L14 14 M6 18 L3 21 M18 6 L21 3", 0.08, "Tech"),
    ("robot", "Robot", "M5 8 L19 8 L19 19 L5 19 Z M9 12 L9 15 M15 12 "
     "L15 15 M10 3 L12 3 L12 8 M8 19 L8 22 M16 19 L16 22 M2 11 L5 11 "
     "M19 11 L22 11", 0.07, "Tech"),
    ("wifi", "Wi-Fi", "M2 9 A15 15 0 0 1 22 9 M5 12 A11 11 0 0 1 19 12 "
     "M8 15 A7 7 0 0 1 16 15 M10 18 A3 3 0 0 1 14 18 M12 21 L12 21.1",
     0.08, "Tech"),
    ("battery", "Battery", "M3 7 L18 7 L18 17 L3 17 Z M20 10 L22 10 "
     "L22 14 L20 14 Z M6 10 L9 10 L9 14 L6 14 Z", 0.06, "Tech"),
    ("bluetooth", "Bluetooth", "M8 5 L16 12 L8 19 L8 5 M16 12 L5 16 "
     "M16 12 L5 8", 0.09, "Tech"),
    ("power", "Power", "M12 3 L12 12 M6 6 A8 8 0 0 0 18 6", 0.08, "Tech"),
    ("signal", "Signal", "M3 20 L3 16 M8 20 L8 12 M13 20 L13 8 M18 20 L18 4",
     0.08, "Tech"),
    # nature and weather ----------------------------------------------
    ("tree", "Tree", "M12 3 L5 12 L9 12 L4 18 L20 18 L15 12 L19 12 Z "
     "M11 18 L11 21 L13 21 L13 18", 0.06, "Nature"),
    ("pine", "Pine", "M12 2 L5 10 L9 10 L4 17 L20 17 L15 10 L19 10 Z "
     "M11 17 L11 21 L13 21 L13 17", 0.06, "Nature"),
    ("mountain", "Mountain", "M2 20 L9 7 L13 14 L16 9 L22 20 Z", 0.06,
     "Nature"),
    ("water", "Water", "M3 7 Q7 4 11 7 T19 7 M3 12 Q7 9 11 12 T19 12 "
     "M3 17 Q7 14 11 17 T19 17", 0.08, "Nature"),
    ("cloud", "Cloud", "M6 18 A4 4 0 0 1 6 10 A5 5 0 0 1 16 9 "
     "A4 4 0 0 1 18 18 Z", 0.06, "Weather"),
    ("rain", "Rain", "M6 15 A4 4 0 0 1 6 7 A5 5 0 0 1 16 6 A4 4 0 0 1 18 15 Z "
     "M8 18 L7 21 M12 18 L11 21 M16 18 L15 21", 0.07, "Weather"),
    ("wind", "Wind", "M3 8 L14 8 A3 3 0 0 0 11 5 M3 14 L18 14 "
     "A2.5 2.5 0 0 1 15.5 16.5 M3 11 L10 11", 0.08, "Weather"),
    ("umbrella", "Umbrella", "M3 12 A9 9 0 0 1 21 12 M12 3 L12 18 "
     "A2 2 0 0 0 16 18", 0.08, "Weather"),
    ("thermometer", "Thermometer", "M10 4 A2 2 0 0 1 14 4 L14 13 "
     "A4 4 0 0 1 10 13 Z M12 7 L12 14", 0.07, "Weather"),
    ("tornado", "Tornado", "M3 5 L21 5 M5 9 L19 9 M7 13 L17 13 "
     "M9 17 L15 17 M11 21 L13 21", 0.08, "Weather"),
    ("sun_rays", "Sun", "M3 12 A9 9 0 0 1 21 12 A9 9 0 0 1 3 12 "
     "M12 1 L12 4 M12 20 L12 23 M1 12 L4 12 M20 12 L23 12", 0.07, "Weather"),
    ("snow_alt", "Snow", "M12 3 L12 21 M4 7 L20 17 M20 7 L4 17", 0.08,
     "Weather"),
    # combat -----------------------------------------------------------
    ("axe", "Axe", "M14 3 C19 4 22 8 22 12 L15 10 Z M14 4 L5 21 L3 20 "
     "L12 3 Z", 0.06, "Combat"),
    ("bow", "Bow", "M4 3 C14 6 18 10 21 20 M4 3 L4 21 M4 21 "
     "C8 18 12 16 15 15 M11 8 L21 20", 0.07, "Combat"),
    ("dagger", "Dagger", "M12 2 L15 8 L14 15 L10 15 L9 8 Z M7 15 L17 15 "
     "L17 18 L7 18 Z M11 18 L11 22 L13 22 L13 18 Z", 0.0, "Combat"),
    ("grenade", "Grenade", "M9 9 A5 5 0 0 1 9 19 A5 5 0 0 1 9 9 "
     "M12 5 L12 9 M9 4 L15 4 M14 3 L17 6 M17 6 L20 3", 0.07, "Combat"),
    ("helmet", "Helmet", "M4 14 A8 8 0 0 1 20 14 L20 19 L4 19 Z "
     "M4 14 L2 16 L4 21 M20 14 L22 16 L20 21", 0.07, "Combat"),
    ("castle", "Castle", "M4 21 L4 8 L7 8 L7 4 L10 4 L10 8 L14 8 L14 4 "
     "L17 4 L17 8 L20 8 L20 21 Z M9 21 L9 15 A3 3 0 0 1 15 15 L15 21",
     0.07, "Combat"),
    ("flag", "Flag", "M5 3 L5 21 M5 4 L19 4 L16 9 L19 14 L5 14", 0.08,
     "Combat"),
    ("spear", "Spear", "M12 2 L15 8 L13 9 L13 20 L11 20 L11 9 L9 8 Z "
     "M8 20 L16 20", 0.0, "Combat"),
    ("mace", "Mace", "M12 3 A5 5 0 0 1 12 13 A5 5 0 0 1 12 3 "
     "M12 8 L12 22 M9 19 L15 19 M8 5 L4 3 M16 5 L20 3 M8 11 L4 13 "
     "M16 11 L20 13", 0.07, "Combat"),
    ("shield_check", "Shield check", "M4 3 L12 1 L20 3 L20 11 C20 16 16 20 "
     "12 22 C8 20 4 16 4 11 Z M8 11 L11 14 L16 8", 0.07, "Combat"),
    # arcane -----------------------------------------------------------
    ("crystal", "Crystal", "M12 2 L18 8 L15 21 L9 21 L6 8 Z M12 2 L12 21 "
     "M6 8 L18 8", 0.06, "Arcane"),
    ("wand", "Wand", "M4 20 L14 10 M12 6 L18 2 M14 10 L18 14 M16 8 L20 8 "
     "M17 5 L19 7", 0.08, "Arcane"),
    ("potion", "Potion", "M9 3 L15 3 L15 7 L18 12 A5 5 0 0 1 8 12 L9 7 Z "
     "M9 13 L15 13", 0.07, "Arcane"),
    ("scroll", "Scroll", "M5 5 L18 5 L20 7 L20 20 L7 20 L5 18 Z "
     "M5 5 A2 2 0 0 0 5 9 L7 9 M18 5 A2 2 0 0 1 18 9 L20 9 "
     "M9 12 L16 12 M9 16 L16 16", 0.07, "Arcane"),
    ("spellbook", "Spellbook", "M4 4 L11 6 L20 4 L20 19 L11 21 L4 19 Z "
     "M11 6 L11 21", 0.07, "Arcane"),
    ("sigil", "Sigil", "M12 2 L14 9 L21 9 L15.5 13 L18 21 L12 16 L6 21 "
     "L8.5 13 L3 9 L10 9 Z", 0.0, "Arcane"),
    ("eclipse", "Eclipse", "M12 3 A9 9 0 0 1 12 21 A9 9 0 0 1 12 3 "
     "M15 3 A9 9 0 0 1 15 21", 0.07, "Arcane"),
    # symbols ----------------------------------------------------------
    ("cross", "Cross", "M10 3 L14 3 L14 10 L21 10 L21 14 L14 14 L14 21 "
     "L10 21 L10 14 L3 14 L3 10 L10 10 Z", 0.0, "Symbols"),
    ("compass_rose", "Compass rose", "M3 12 A9 9 0 0 1 21 12 "
     "A9 9 0 0 1 3 12 M12 2 L14 10 L22 12 L14 14 L12 22 L10 14 L2 12 "
     "L10 10 Z", 0.05, "Symbols"),
    ("globe", "Globe", "M3 12 A9 9 0 0 1 21 12 A9 9 0 0 1 3 12 "
     "M3 12 L21 12 M12 3 C8 7 8 17 12 21 M12 3 C16 7 16 17 12 21", 0.06,
     "Symbols"),
    ("map", "Map", "M3 5 L9 3 L15 5 L21 3 L21 19 L15 21 L9 19 L3 21 Z "
     "M9 3 L9 19 M15 5 L15 21", 0.06, "Symbols"),
    ("meteor", "Meteor", "M14 4 A6 6 0 0 1 14 16 A6 6 0 0 1 14 4 "
     "M10 12 L2 20 M9 8 L2 11 M14 15 L8 22", 0.07, "Symbols"),
    ("vortex", "Vortex", "M12 3 C18 3 21 7 21 12 C21 17 17 21 12 21 "
     "C7 21 3 17 3 12 C3 8 6 5 10 5 C13 5 15 7 15 10 C15 12 13 14 11 14 "
     "C9 14 8 13 8 11", 0.07, "Symbols"),
    ("book", "Book", "M4 4 L11 6 L20 4 L20 19 L11 21 L4 19 Z M11 6 L11 21",
     0.07, "Symbols"),
    # music ------------------------------------------------------------
    ("note", "Note", "M9 18 L9 4 L20 2 L20 16 M9 8 L20 6 M6 18 A3 3 0 0 1 "
     "12 18 A3 3 0 0 1 6 18 M17 16 A3 3 0 0 1 23 16 A3 3 0 0 1 17 16",
     0.05, "Music"),
    ("music", "Music", "M9 18 L9 5 L20 3 L20 16 M9 9 L20 7 M6 18 A3 3 0 0 1 "
     "12 18 A3 3 0 0 1 6 18", 0.06, "Music"),
    ("guitar", "Guitar", "M9 3 L11 3 L11 11 A5 5 0 0 1 9 11 Z M15 3 L15 9 "
     "M13 3 L17 3 M13 9 L17 9", 0.07, "Music"),
    ("piano", "Piano", "M3 5 L21 5 L21 19 L3 19 Z M6 5 L6 12 M10 5 L10 12 "
     "M14 5 L14 12 M18 5 L18 12", 0.07, "Music"),
    ("drum", "Drum", "M4 9 A8 4 0 0 1 20 9 L20 15 A8 4 0 0 1 4 15 Z "
     "M4 9 A8 4 0 0 0 20 9 M6 19 L4 22 M18 19 L20 22", 0.07, "Music"),
    ("vinyl", "Vinyl", "M3 12 A9 9 0 0 1 21 12 A9 9 0 0 1 3 12 "
     "M12 9 A3 3 0 0 1 12 15 A3 3 0 0 1 12 9", 0.06, "Music"),
    ("headphones", "Headphones", "M4 14 L4 11 A8 8 0 0 1 20 11 L20 14 "
     "M4 14 L4 19 L8 19 L8 14 Z M20 14 L20 19 L16 19 L16 14 Z", 0.07,
     "Music"),
    # commerce ---------------------------------------------------------
    ("cart", "Cart", "M3 4 L6 4 L9 15 L19 15 L21 7 L7 7 M9 19 A1.5 1.5 "
     "0 0 1 9 22 A1.5 1.5 0 0 1 9 19 M18 19 A1.5 1.5 0 0 1 18 22 "
     "A1.5 1.5 0 0 1 18 19", 0.07, "Commerce"),
    ("bag", "Bag", "M5 8 L19 8 L21 21 L3 21 Z M8 8 L8 5 A4 4 0 0 1 16 5 "
     "L16 8", 0.08, "Commerce"),
    ("card", "Card", "M3 5 L21 5 L21 19 L3 19 Z M3 9 L21 9 M6 15 L11 15",
     0.07, "Commerce"),
    ("coin", "Coin", "M12 3 A9 9 0 0 1 12 21 A9 9 0 0 1 12 3 "
     "M12 7 L12 17 M9 10 L15 10 M9 14 L15 14", 0.07, "Commerce"),
    ("gift", "Gift", "M3 9 L21 9 L21 13 L3 13 Z M5 13 L5 21 L19 21 L19 13 "
     "M12 9 L12 21 M12 9 C8 9 6 7 7 5 C8 3 12 5 12 9 M12 9 "
     "C16 9 18 7 17 5 C16 3 12 5 12 9", 0.07, "Commerce"),
    ("wallet", "Wallet", "M3 6 L18 6 L21 9 L21 19 L3 19 Z M3 10 L21 10 "
     "M16 13 L18 13 L18 16 L16 16 Z", 0.07, "Commerce"),
    ("receipt", "Receipt", "M5 3 L19 3 L19 21 L16 19 L13 21 L10 19 "
     "L7 21 L5 19 Z M8 8 L16 8 M8 12 L16 12 M8 16 L13 16", 0.07,
     "Commerce"),
    ("bank", "Bank", "M3 9 L12 3 L21 9 Z M5 9 L5 18 M9 9 L9 18 M15 9 L15 18 "
     "M19 9 L19 18 M3 21 L21 21", 0.07, "Commerce"),
)
