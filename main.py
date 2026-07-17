import importlib.util
import re
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional


def _ask_to_install(package_name: str, import_name: str) -> bool:
    if importlib.util.find_spec(import_name) is not None:
        return True

    print(f"Missing dependency: {package_name}")

    while True:
        try:
            answer = input(
                f"Download and install {package_name} now? (y/n): "
            ).strip().lower()
        except (EOFError, OSError):
            print(
                "No interactive console is available.\n"
                f'Install manually with:\n'
                f'  "{sys.executable}" -m pip install {package_name}'
            )
            return False

        if answer in {"y", "yes"}:
            try:
                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        package_name,
                    ]
                )
            except (OSError, subprocess.CalledProcessError) as exc:
                print(f"Could not install {package_name}: {exc}")
                return False

            return importlib.util.find_spec(import_name) is not None

        if answer in {"n", "no"}:
            return False

        print("Please enter y or n.")


def _check_dependencies() -> None:
    missing = []

    if not _ask_to_install("protobuf", "google.protobuf"):
        missing.append("protobuf")

    if not _ask_to_install("lz4", "lz4"):
        missing.append("lz4")

    if not _ask_to_install("pyinstaller", "PyInstaller"):
        missing.append("pyinstaller")

    if missing:
        raise SystemExit(
            "Required dependencies are unavailable: "
            + ", ".join(missing)
        )


if __name__ == "__main__" and not getattr(sys, "frozen", False):
    _check_dependencies()


from utils import (
    BCS_LABEL_TO_VALUE,
    BCS_VALUE_OPTIONS,
    BCS_VALUE_TO_LABEL,
    DL_LABEL_TO_VALUE,
    DL_VALUE_OPTIONS,
    DL_VALUE_TO_LABEL,
    UL_VALUE_OPTIONS,
    UL_VALUE_TO_LABEL,
    Combo,
    ComboDocument,
    Component,
    ParseError,
    copy_combo,
    count_direction_components,
    describe_bcs_mask,
    describe_direction_combo,
    describe_dl_mimo,
    format_binary_document,
    format_document,
    generate_ul_variants,
    parse_binary_document,
    parse_document,
)

from conf_id import (
    CONF_ID_NAMES,
    conf_ids_to_masks,
    masks_to_conf_ids,
)

from s5300_confseq import (
    S5300_UL_AUTO_VALUE,
    S5300Bundle,
    discover_s5300_families,
    export_s5300_bundle,
    load_s5300_bundle,
)

from tools_ui import (
    open_auto_generate_dialog,
    open_combo_pruning_dialog,
    open_conf_id_dialog,
    run_validate_tool,
)

S5300_UL_VALUE_OPTIONS = [
    ("0", "0 (None)"),
    ("32768", "32768 (A)"),
    ("16384", "16384 (B)"),
    ("8192", "8192 (C)"),
    ("4096", "4096 (D)"),
    (str(S5300_UL_AUTO_VALUE), "Auto PCC (all bands)"),
]


class ComboEditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Shannon LTE CA editor")
        self.geometry("1320x720")
        self.minsize(1320, 720)

        self.document = ComboDocument()
        self.current_path: Optional[Path] = None
        self.s5300_bundle: Optional[S5300Bundle] = None
        self.s5300_family: Optional[str] = None
        self.conf_id_names = dict(CONF_ID_NAMES)
        self.selected_combo_index: Optional[int] = None
        self.selected_component_index: Optional[int] = None

        self.version_var = tk.StringVar(value="0")
        self.bitmask_var = tk.StringVar(value="0")

        self.bcs_var = tk.StringVar(
            value=BCS_VALUE_TO_LABEL["2147483648"]
        )
        self.configMaskLow_var = tk.StringVar(
            value="18445899642336968703"
        )
        self.configMaskHigh_var = tk.StringVar(
            value="2097151"
        )

        self.band_var = tk.StringVar(value="1")
        self.dl_var = tk.StringVar(
            value=DL_VALUE_TO_LABEL["32768"]
        )
        self.ul_var = tk.StringVar(
            value=UL_VALUE_TO_LABEL["0"]
        )

        self.search_var = tk.StringVar(value="")

        self.plmn_filter_label_var = tk.StringVar(
            value="PLMN filter"
        )
        self.selected_plmn_conf_ids: set[int] = set()

        self.status_var = tk.StringVar(value="Ready")
        self.component_cell_editor: Optional[tk.Widget] = None

        self._build_menu()
        self._build_ui()
        self._bind_shortcuts()
        self.refresh_all()

    def _build_menu(self) -> None:
        menu = tk.Menu(self)

        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(
            label="New",
            command=self.new_document,
            accelerator="Ctrl+N",
        )
        file_menu.add_command(
            label="Import .binarypb...",
            command=self.import_decoded_txt,
            accelerator="Ctrl+O",
        )
        file_menu.add_command(
            label="Import .txt...",
            command=self.import_text_file,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Import S5300 confseq folder...",
            command=self.import_s5300_confseq_folder,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Save",
            command=self.save_file,
            accelerator="Ctrl+S",
        )
        file_menu.add_command(
            label="Export .binarypb...",
            command=self.save_binary_file,
        )
        file_menu.add_command(
            label="Export .txt...",
            command=self.save_text_file,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Export S5300 confseq folder...",
            command=self.export_s5300_confseq_folder,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Exit",
            command=self.destroy,
        )

        menu.add_cascade(
            label="File",
            menu=file_menu,
        )

        self.config(menu=menu)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)

        metadata = ttk.LabelFrame(
            outer,
            text="Information",
            padding=8,
        )
        metadata.pack(fill="x", pady=(0, 10))

        ttk.Label(
            metadata,
            text="Version",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Entry(
            metadata,
            textvariable=self.version_var,
            width=18,
            state="readonly",
        ).grid(
            row=0,
            column=1,
            padx=(6, 20),
        )

        ttk.Label(
            metadata,
            text="Bitmask",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        ttk.Entry(
            metadata,
            textvariable=self.bitmask_var,
            width=18,
            state="readonly",
        ).grid(
            row=0,
            column=3,
            padx=(6, 20),
        )

        ttk.Button(
            metadata,
            text="Auto generate combos",
            command=self.open_auto_generate_tool,
        ).grid(
            row=0,
            column=4,
            padx=(10, 6),
        )

        ttk.Button(
            metadata,
            text="Combo pruning",
            command=self.open_combo_pruning_tool,
        ).grid(
            row=0,
            column=5,
            padx=(0, 6),
        )

        ttk.Button(
            metadata,
            text="Apply conf_id to combos",
            command=self.open_apply_conf_id_tool,
        ).grid(
            row=0,
            column=6,
            padx=(0, 6),
        )

        ttk.Button(
            metadata,
            text="Validate",
            command=self.validate_all_combos,
        ).grid(
            row=0,
            column=7,
            padx=(0, 10),
        )

        metadata.columnconfigure(
            8,
            weight=1,
        )

        ttk.Button(
            metadata,
            text="Import .binarypb",
            command=self.import_decoded_txt,
        ).grid(
            row=0,
            column=9,
            padx=(6, 6),
        )

        ttk.Button(
            metadata,
            text="Export .binarypb",
            command=self.save_binary_file,
        ).grid(
            row=0,
            column=10,
            padx=(0, 6),
        )

        ttk.Button(
            metadata,
            text="Import .txt",
            command=self.import_text_file,
        ).grid(
            row=0,
            column=11,
            padx=(0, 6),
        )

        ttk.Button(
            metadata,
            text="Export .txt",
            command=self.save_text_file,
        ).grid(
            row=0,
            column=12,
        )

        paned = ttk.Panedwindow(
            outer,
            orient="horizontal",
        )
        paned.pack(fill="both", expand=True)

        left = ttk.Frame(
            paned,
            padding=(0, 0, 5, 0),
        )
        right = ttk.Frame(
            paned,
            padding=(5, 0, 0, 0),
        )

        paned.add(left, weight=3)
        paned.add(right, weight=1)

        self.after_idle(
            lambda: paned.sashpos(0, 910)
        )

        self._build_search_bar(left)
        self._build_combo_table(left)
        self._build_combo_buttons(left)
        self._build_combo_editor(right)
        self._build_component_editor(right)

        status = ttk.Label(
            self,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            padding=(8, 3),
        )
        status.pack(
            fill="x",
            side="bottom",
        )

    def _build_search_bar(self, parent: ttk.Widget) -> None:
        search_frame = ttk.Frame(parent)
        search_frame.pack(
            fill="x",
            pady=(0, 6),
        )

        ttk.Label(
            search_frame,
            text="Search",
        ).pack(side="left")

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
        )
        search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(8, 6),
        )

        ttk.Button(
            search_frame,
            textvariable=self.plmn_filter_label_var,
            command=self.open_plmn_filter,
        ).pack(
            side="left",
            padx=(6, 6),
        )

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_filters,
        ).pack(side="left")

        self.search_var.trace_add(
            "write",
            lambda *_args: self.refresh_combo_tree(),
        )

    def _build_combo_table(self, parent: ttk.Widget) -> None:
        combo_frame = ttk.LabelFrame(
            parent,
            text="LTE Combos",
            padding=6,
        )
        combo_frame.pack(
            fill="both",
            expand=True,
        )

        columns = (
            "index",
            "dl_combo",
            "dl_mimo",
            "ul_combo",
            "dl_ccs",
            "ul_ccs",
            "bcs",
            "configMaskLow",
            "configMaskHigh",
        )

        self.combo_tree = ttk.Treeview(
            combo_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "index": "#",
            "dl_combo": "DL Combo",
            "dl_mimo": "DL MIMO",
            "ul_combo": "UL Combo",
            "dl_ccs": "DL CCs",
            "ul_ccs": "UL CCs",
            "bcs": "BCS",
            "configMaskLow": "Conf ID 1",
            "configMaskHigh": "Conf ID 2",
        }

        widths = {
            "index": 45,
            "dl_combo": 150,
            "dl_mimo": 150,
            "ul_combo": 150,
            "dl_ccs": 50,
            "ul_ccs": 50,
            "bcs": 80,
            "configMaskLow": 140,
            "configMaskHigh": 90,
        }

        for name in columns:
            self.combo_tree.heading(
                name,
                text=headings[name],
            )
            self.combo_tree.column(
                name,
                width=widths[name],
                anchor="center",
            )

        combo_scroll = ttk.Scrollbar(
            combo_frame,
            orient="vertical",
            command=self.combo_tree.yview,
        )

        self.combo_tree.configure(
            yscrollcommand=combo_scroll.set,
        )

        self.combo_tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        combo_scroll.pack(
            side="right",
            fill="y",
        )

        self.combo_tree.bind(
            "<<TreeviewSelect>>",
            self.on_combo_selected,
        )
        self.combo_tree.bind(
            "<Delete>",
            self.on_delete_combo_key,
        )

    def _build_combo_buttons(self, parent: ttk.Widget) -> None:
        combo_buttons = ttk.Frame(parent)
        combo_buttons.pack(
            fill="x",
            pady=(8, 0),
        )

        ttk.Button(
            combo_buttons,
            text="Add combo",
            command=self.add_combo,
        ).pack(side="left")

        ttk.Button(
            combo_buttons,
            text="Duplicate",
            command=self.duplicate_combo,
        ).pack(
            side="left",
            padx=6,
        )

        ttk.Button(
            combo_buttons,
            text="Auto fill UL band",
            command=self.auto_fill_ul_band,
        ).pack(
            side="left",
            padx=(0, 6),
        )

        ttk.Button(
            combo_buttons,
            text="Auto fill ULCA",
            command=self.auto_fill_ulca,
        ).pack(
            side="left",
            padx=(0, 6),
        )

        ttk.Button(
            combo_buttons,
            text="Delete",
            command=self.delete_combo,
        ).pack(side="left")

        ttk.Button(
            combo_buttons,
            text="Move up",
            command=lambda: self.move_combo(-1),
        ).pack(side="right")

        ttk.Button(
            combo_buttons,
            text="Move down",
            command=lambda: self.move_combo(1),
        ).pack(
            side="right",
            padx=6,
        )

    def _build_combo_editor(self, parent: ttk.Widget) -> None:
        combo_editor = ttk.LabelFrame(
            parent,
            text="Selected combo",
            padding=10,
        )
        combo_editor.pack(fill="x")

        ttk.Label(
            combo_editor,
            text="BCS",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=3,
        )

        self.bcs_combobox = ttk.Combobox(
            combo_editor,
            textvariable=self.bcs_var,
            values=[
                label
                for _value, label in BCS_VALUE_OPTIONS
            ],
            state="readonly",
        )
        self.bcs_combobox.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(8, 0),
            pady=3,
        )

        self.bcs_combobox.bind(
            "<<ComboboxSelected>>",
            self.on_bcs_value_changed,
        )

        self.config_mask_low_entry = self._labeled_entry(
            combo_editor,
            "Conf ID 1",
            self.configMaskLow_var,
            1,
        )

        self.config_mask_high_entry = self._labeled_entry(
            combo_editor,
            "Conf ID 2",
            self.configMaskHigh_var,
            2,
        )

        self.config_mask_low_entry.bind(
            "<Return>",
            lambda _event: self.apply_combo_fields(),
        )
        self.config_mask_high_entry.bind(
            "<Return>",
            lambda _event: self.apply_combo_fields(),
        )

        self.config_mask_low_entry.bind(
            "<KP_Enter>",
            lambda _event: self.apply_combo_fields(),
        )
        self.config_mask_high_entry.bind(
            "<KP_Enter>",
            lambda _event: self.apply_combo_fields(),
        )

        ttk.Button(
            combo_editor,
            text="Set combo fields",
            command=self.apply_combo_fields,
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )

        ttk.Button(
            combo_editor,
            text="Find conf_id mapping",
            command=self.open_conf_id_mapper,
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(6, 0),
        )

        combo_editor.columnconfigure(
            1,
            weight=1,
        )

    def _build_component_editor(
        self,
        parent: ttk.Widget,
    ) -> None:
        component_frame = ttk.LabelFrame(
            parent,
            text="Band Components",
            padding=8,
        )

        component_frame.pack(
            fill="both",
            expand=True,
            pady=(10, 0),
        )

        table_frame = ttk.Frame(
            component_frame
        )

        table_frame.pack(
            fill="both",
            expand=True,
        )

        component_columns = (
            "index",
            "band",
            "dl",
            "ul",
        )

        self.component_tree = ttk.Treeview(
            table_frame,
            columns=component_columns,
            show="headings",
            selectmode="browse",
            height=12,
        )

        for name, heading, width in (
            ("index", "#", 35),
            ("band", "Band", 60),
            ("dl", "DL class/MIMO", 150),
            ("ul", "UL class", 130),
        ):
            self.component_tree.heading(
                name,
                text=heading,
            )

            self.component_tree.column(
                name,
                width=width,
                anchor="center",
            )

        component_scroll = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.component_tree.yview,
        )

        self.component_tree.configure(
            yscrollcommand=component_scroll.set,
        )

        self.component_tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        component_scroll.pack(
            side="right",
            fill="y",
        )

        self.component_tree.bind(
            "<<TreeviewSelect>>",
            self.on_component_selected,
        )

        self.component_tree.bind(
            "<Button-1>",
            self._on_component_cell_click,
        )

        self.component_tree.bind(
            "<Delete>",
            self.on_delete_component_key,
        )

        self.component_tree.bind(
            "<MouseWheel>",
            lambda _event: (
                self._close_component_cell_editor()
            ),
        )

        component_buttons = ttk.Frame(
            component_frame
        )

        component_buttons.pack(
            fill="x",
            pady=(8, 0),
        )

        ttk.Button(
            component_buttons,
            text="Add band",
            command=self.add_component,
        ).pack(
            side="left"
        )

        ttk.Button(
            component_buttons,
            text="Delete",
            command=self.delete_component,
        ).pack(
            side="left",
            padx=(6, 0),
        )

        ttk.Button(
            component_buttons,
            text="Move up",
            command=lambda: (
                self.move_component(-1)
            ),
        ).pack(
            side="right"
        )

        ttk.Button(
            component_buttons,
            text="Move down",
            command=lambda: (
                self.move_component(1)
            ),
        ).pack(
            side="right",
            padx=6,
        )


    def _close_component_cell_editor(
        self,
    ) -> None:
        editor = self.component_cell_editor

        if editor is not None:
            try:
                editor.destroy()
            except tk.TclError:
                pass

        self.component_cell_editor = None


    def _on_component_cell_click(
        self,
        event: tk.Event,
    ) -> Optional[str]:
        active_editor = self.component_cell_editor

        # A click inside the same Treeview may not trigger FocusOut
        # because this handler returns "break". Commit an active
        # Band entry manually before opening another cell editor.
        if isinstance(
            active_editor,
            ttk.Entry,
        ):
            commit_callback = getattr(
                active_editor,
                "commit_value",
                None,
            )

            if commit_callback is not None:
                commit_callback()

                # If the editor is still active, validation failed.
                if self.component_cell_editor is active_editor:
                    return "break"

        row_id = self.component_tree.identify_row(
            event.y
        )

        column_id = self.component_tree.identify_column(
            event.x
        )

        if not row_id:
            self._close_component_cell_editor()
            return None

        # Row-number column: allow normal Treeview selection.
        if column_id == "#1":
            self._close_component_cell_editor()
            return None

        if column_id not in {
            "#2",
            "#3",
            "#4",
        }:
            self._close_component_cell_editor()
            return None

        try:
            component_index = int(
                row_id
            )
        except ValueError:
            return "break"

        combo = self.get_selected_combo()

        if combo is None:
            return "break"

        if not (
            0
            <= component_index
            < len(combo.components)
        ):
            return "break"

        self.selected_component_index = (
            component_index
        )

        self.component_tree.selection_set(
            row_id
        )

        self.component_tree.focus(
            row_id
        )

        self.component_tree.see(
            row_id
        )

        self.after_idle(
            lambda: self._begin_component_cell_edit(
                row_id=row_id,
                column_id=column_id,
                component_index=component_index,
            )
        )

        return "break"


    def _begin_component_cell_edit(
        self,
        row_id: str,
        column_id: str,
        component_index: int,
    ) -> None:
        self._close_component_cell_editor()

        combo = self.get_selected_combo()

        if combo is None:
            return

        if not (
            0
            <= component_index
            < len(combo.components)
        ):
            return

        bbox = self.component_tree.bbox(
            row_id,
            column_id,
        )

        if not bbox:
            return

        x, y, width, height = bbox

        component = combo.components[
            component_index
        ]

        if column_id == "#2":
            editor = ttk.Entry(
                self.component_tree
            )

            editor.insert(
                0,
                str(component.band),
            )

            editor.select_range(
                0,
                "end",
            )

            commit_in_progress = False

            def commit_band(
                _event=None,
            ) -> None:
                nonlocal commit_in_progress

                if commit_in_progress:
                    return

                try:
                    band = int(
                        editor.get().strip(),
                        10,
                    )

                except ValueError:
                    messagebox.showerror(
                        "Invalid band",
                        "Band must be a positive integer.",
                        parent=self,
                    )

                    editor.focus_set()
                    return

                if band <= 0:
                    messagebox.showerror(
                        "Invalid band",
                        "Band must be a positive integer.",
                        parent=self,
                    )

                    editor.focus_set()
                    return

                commit_in_progress = True

                component.band = band

                self._finish_component_cell_edit(
                    component_index,
                    f"Band changed to {band}",
                )

            # Store the callback so clicks inside the Treeview
            # can commit the Band entry manually.
            editor.commit_value = commit_band

            editor.bind(
                "<Return>",
                commit_band,
            )

            editor.bind(
                "<KP_Enter>",
                commit_band,
            )

            editor.bind(
                "<FocusOut>",
                commit_band,
            )

        elif column_id == "#3":
            editor = ttk.Combobox(
                self.component_tree,
                values=[
                    label
                    for _value, label
                    in DL_VALUE_OPTIONS
                ],
                state="readonly",
                height=len(DL_VALUE_OPTIONS),
            )

            editor.set(
                DL_VALUE_TO_LABEL.get(
                    str(component.bwClassMimoDl),
                    str(component.bwClassMimoDl),
                )
            )

            def commit_dl(
                _event=None,
            ) -> None:
                raw_value = DL_LABEL_TO_VALUE.get(
                    editor.get()
                )

                if raw_value is None:
                    return

                component.bwClassMimoDl = int(
                    raw_value
                )

                self._finish_component_cell_edit(
                    component_index,
                    "DL class/MIMO updated",
                )

            editor.bind(
                "<<ComboboxSelected>>",
                commit_dl,
            )

            editor.bind(
                "<Return>",
                commit_dl,
            )

            editor.bind(
                "<KP_Enter>",
                commit_dl,
            )

        else:
            ul_options = self._ul_value_options()
            editor = ttk.Combobox(
                self.component_tree,
                values=[
                    label
                    for _value, label
                    in ul_options
                ],
                state="readonly",
            )

            editor.set(
                self._ul_label(component.bwClassMimoUl)
            )

            def commit_ul(
                _event=None,
            ) -> None:
                raw_value = self._ul_label_to_value().get(
                    editor.get()
                )

                if raw_value is None:
                    return

                self._set_component_ul_value(
                    combo,
                    component_index,
                    int(raw_value),
                )

                self._finish_component_cell_edit(
                    component_index,
                    "UL class updated",
                )

            editor.bind(
                "<<ComboboxSelected>>",
                commit_ul,
            )

            editor.bind(
                "<Return>",
                commit_ul,
            )

            editor.bind(
                "<KP_Enter>",
                commit_ul,
            )

        editor.bind(
            "<Escape>",
            lambda _event: (
                self._close_component_cell_editor()
            ),
        )

        editor.place(
            x=x,
            y=y,
            width=width,
            height=height,
        )

        self.component_cell_editor = editor

        editor.focus_set()

        if isinstance(
            editor,
            ttk.Combobox,
        ):
            def open_dropdown(
                current_editor=editor,
            ) -> None:
                try:
                    if not current_editor.winfo_exists():
                        return

                    current_editor.focus_force()

                    current_editor.tk.call(
                        "ttk::combobox::Post",
                        current_editor._w,
                    )

                except tk.TclError:
                    pass

            self.after_idle(
                open_dropdown
            )


    def _finish_component_cell_edit(
        self,
        component_index: int,
        status_message: str,
    ) -> None:
        self._close_component_cell_editor()

        combo = self.get_selected_combo()

        if combo is None:
            return

        if not (
            0
            <= component_index
            < len(combo.components)
        ):
            return

        self.selected_component_index = (
            component_index
        )

        component_row_id = str(
            component_index
        )

        # Auto PCC is a combo-level mode, so changing one UL cell can update
        # every component row.
        for row_index, component in enumerate(combo.components):
            row_id = str(row_index)
            if not self.component_tree.exists(row_id):
                continue
            dl_label = DL_VALUE_TO_LABEL.get(
                str(component.bwClassMimoDl),
                str(component.bwClassMimoDl),
            )
            self.component_tree.item(
                row_id,
                values=(
                    row_index + 1,
                    component.band,
                    dl_label,
                    self._ul_label(component.bwClassMimoUl),
                ),
            )

        if self.component_tree.exists(component_row_id):
            self.component_tree.selection_set(
                component_row_id
            )

            self.component_tree.focus(
                component_row_id
            )

            self.component_tree.see(
                component_row_id
            )

        # Update the corresponding main combo row without
        # selecting it or triggering on_combo_selected().
        combo_index = self.selected_combo_index

        if combo_index is not None:
            combo_row_id = str(
                combo_index
            )

            if self.combo_tree.exists(
                combo_row_id
            ):
                self.combo_tree.item(
                    combo_row_id,
                    values=self._combo_row_values(
                        combo_index,
                        combo,
                    ),
                )

        self.load_component_editor()

        self.status_var.set(
            status_message
        )

    @staticmethod
    def _labeled_entry(
        parent: ttk.Widget,
        label: str,
        variable: tk.StringVar,
        row: int,
    ) -> ttk.Entry:
        ttk.Label(
            parent,
            text=label,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=3,
        )

        entry = ttk.Entry(
            parent,
            textvariable=variable,
        )
        entry.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=(8, 0),
            pady=3,
        )

        return entry
    
    def _on_document_tool_changed(
        self,
        message: str,
    ) -> None:
        self.selected_combo_index = None
        self.selected_component_index = None

        self.refresh_all()

        self.status_var.set(
            message.replace(
                "\n",
                " | ",
            )
        )

    def open_auto_generate_tool(
        self,
    ) -> None:
        open_auto_generate_dialog(
            parent=self,
            document=self.document,
            on_changed=(
                self._on_document_tool_changed
            ),
        )

    def open_combo_pruning_tool(
        self,
    ) -> None:
        if not self.document.combos:
            messagebox.showinfo(
                "No combinations",
                "There are no combinations to prune.",
                parent=self,
            )
            return

        open_combo_pruning_dialog(
            parent=self,
            document=self.document,
            on_changed=(
                self._on_document_tool_changed
            ),
        )

    def open_apply_conf_id_tool(
        self,
    ) -> None:
        if not self.document.combos:
            messagebox.showinfo(
                "No combinations",
                (
                    "There are no combinations to "
                    "apply conf_id values to."
                ),
                parent=self,
            )
            return

        open_conf_id_dialog(
            parent=self,
            document=self.document,
            conf_id_names=self.conf_id_names,
            on_changed=(
                self._on_document_tool_changed
            ),
        )

    def validate_all_combos(
        self,
    ) -> None:
        if not self.document.combos:
            messagebox.showinfo(
                "No combinations",
                "There are no combinations to validate.",
                parent=self,
            )
            return

        run_validate_tool(
            parent=self,
            document=self.document,
            on_changed=self._on_document_tool_changed,
            on_highlight=self._highlight_validation_issues,
        )
        
    def _highlight_validation_issues(
        self,
        combo_indices: set[int],
    ) -> None:
        self.combo_tree.selection_remove(
            *self.combo_tree.selection()
        )

        matched_items: list[str] = []

        for item_id in self.combo_tree.get_children():
            values = self.combo_tree.item(
                item_id,
                "values",
            )

            if not values:
                continue

            try:
                displayed_number = int(
                    values[0]
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            document_index = (
                displayed_number - 1
            )

            if document_index in combo_indices:
                matched_items.append(
                    item_id
                )

        if not matched_items:
            self.status_var.set(
                "Validation issues exist, but the affected "
                "rows are hidden by the current search/filter."
            )
            return

        self.combo_tree.selection_set(
            matched_items
        )

        self.combo_tree.focus(
            matched_items[0]
        )

        self.combo_tree.see(
            matched_items[0]
        )

        self.status_var.set(
            f"Highlighted {len(matched_items)} "
            "affected combo row(s)."
        )

    def _bind_shortcuts(self) -> None:
        self.bind_all(
            "<Control-n>",
            lambda _event: self.new_document(),
        )
        self.bind_all(
            "<Control-o>",
            lambda _event: self.import_decoded_txt(),
        )
        self.bind_all(
            "<Control-s>",
            lambda _event: self.save_binary_file(),
        )

    @staticmethod
    def _int_value(
        value: str,
        field_name: str,
    ) -> int:
        try:
            return int(value.strip(), 10)
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must be a decimal integer"
            ) from exc

    @staticmethod
    def _dropdown_value(
        displayed_value: str,
        label_to_value: dict[str, str],
        field_name: str,
    ) -> int:
        raw_value = label_to_value.get(displayed_value)

        if raw_value is None:
            raise ValueError(
                f"Select a valid {field_name} option"
            )

        return int(raw_value)

    @staticmethod
    def _dropdown_label(
        raw_value: int,
        value_to_label: dict[str, str],
    ) -> str:
        key = str(raw_value)
        return value_to_label.get(key, key)

    def _ul_value_options(self) -> list[tuple[str, str]]:
        if self.s5300_family is not None:
            return S5300_UL_VALUE_OPTIONS
        return UL_VALUE_OPTIONS

    def _ul_value_to_label(self) -> dict[str, str]:
        return dict(self._ul_value_options())

    def _ul_label_to_value(self) -> dict[str, str]:
        return {
            label: value
            for value, label in self._ul_value_options()
        }

    def _ul_label(self, value: int) -> str:
        return self._dropdown_label(
            value,
            self._ul_value_to_label(),
        )

    def _is_s5300_auto_ul_combo(self, combo: Combo) -> bool:
        return (
            self.s5300_family is not None
            and bool(combo.components)
            and all(
                component.bwClassMimoUl == S5300_UL_AUTO_VALUE
                for component in combo.components
            )
        )

    def _set_component_ul_value(
        self,
        combo: Combo,
        component_index: int,
        value: int,
    ) -> None:
        if self.s5300_family is not None:
            if value == S5300_UL_AUTO_VALUE:
                for component in combo.components:
                    component.bwClassMimoUl = S5300_UL_AUTO_VALUE
                return
            if self._is_s5300_auto_ul_combo(combo):
                for component in combo.components:
                    component.bwClassMimoUl = 0

        combo.components[component_index].bwClassMimoUl = value

    @staticmethod
    def _normalize_search_text(value: str) -> str:
        return re.sub(
            r"\s+",
            "",
            value,
        ).upper()

    def apply_document_fields(self) -> None:
        try:
            self.document.version = self._int_value(
                self.version_var.get(),
                "Version",
            )
            self.document.bitmask = self._int_value(
                self.bitmask_var.get(),
                "Bitmask",
            )
        except ValueError as exc:
            messagebox.showerror(
                "Invalid value",
                str(exc),
            )
            return

        self.status_var.set(
            "Document fields updated"
        )

    def refresh_all(
        self,
        select_combo: Optional[int] = None,
    ) -> None:
        self.version_var.set(
            str(self.document.version)
        )
        self.bitmask_var.set(
            str(self.document.bitmask)
        )

        self.refresh_combo_tree(select_combo)
        self.refresh_component_tree()

        self.status_var.set(
            f"{len(self.document.combos)} combinations loaded"
        )

    def _combo_row_values(
        self,
        index: int,
        combo: Combo,
    ) -> tuple:
        if self._is_s5300_auto_ul_combo(combo):
            auto_ul_bands = list(dict.fromkeys(
                component.band for component in combo.components
            ))
            ul_description = "Auto PCC (" + " / ".join(
                str(band) for band in auto_ul_bands
            ) + ")"
            ul_component_count = 1
        else:
            ul_description = describe_direction_combo(
                combo,
                "bwClassMimoUl",
            )
            ul_component_count = count_direction_components(
                combo,
                "bwClassMimoUl",
            )

        return (
            index + 1,
            describe_direction_combo(
                combo,
                "bwClassMimoDl",
            ),
            describe_dl_mimo(combo),
            ul_description,
            count_direction_components(
                combo,
                "bwClassMimoDl",
            ),
            ul_component_count,
            describe_bcs_mask(combo.bcs),
            str(combo.configMaskLow),
            str(combo.configMaskHigh),
        )

    def clear_filters(self) -> None:
        self.search_var.set("")
        self.selected_plmn_conf_ids.clear()
        self.plmn_filter_label_var.set(
            "PLMN filter"
        )
        self.refresh_combo_tree()

    def _combo_matches_filters(
        self,
        index: int,
        combo: Combo,
    ) -> bool:
        query = self.search_var.get().strip()

        if query:
            normalized_query = self._normalize_search_text(
                query
            )
            row_values = self._combo_row_values(
                index,
                combo,
            )

            text_matches = any(
                normalized_query
                in self._normalize_search_text(str(value))
                for value in row_values
            )

            if not text_matches:
                return False

        if self.selected_plmn_conf_ids:
            combo_conf_ids = masks_to_conf_ids(
                combo.configMaskLow,
                combo.configMaskHigh,
            )

            if not combo_conf_ids.intersection(
                self.selected_plmn_conf_ids
            ):
                return False

        return True

    def open_plmn_filter(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("PLMN filter")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        outer = ttk.Frame(
            dialog,
            padding=12,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            outer,
            text=(
                "Show combinations enabled for any selected "
                "PLMN/conf_id mapping."
            ),
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        checkbox_frame = ttk.LabelFrame(
            outer,
            text="Select PLMN/conf_id mappings",
            padding=8,
        )

        checkbox_frame.pack(
            fill="both",
            expand=True,
        )

        checkbox_vars: dict[
            int,
            tk.BooleanVar,
        ] = {}

        visible_conf_ids = [
            conf_id
            for conf_id in sorted(
                self.conf_id_names
            )
            if conf_id != 0
        ]

        for display_index, conf_id in enumerate(
            visible_conf_ids
        ):
            row = display_index % 10
            column = display_index // 10

            variable = tk.BooleanVar(
                value=(
                    conf_id
                    in self.selected_plmn_conf_ids
                )
            )

            checkbox_vars[
                conf_id
            ] = variable

            ttk.Checkbutton(
                checkbox_frame,
                text=(
                    f"{self.conf_id_names[conf_id]} "
                    f"({conf_id})"
                ),
                variable=variable,
            ).grid(
                row=row,
                column=column,
                sticky="w",
                padx=(0, 12),
                pady=2,
            )

        for column in range(9):
            checkbox_frame.columnconfigure(
                column,
                weight=1,
            )

        def reset_filter() -> None:
            for variable in (
                checkbox_vars.values()
            ):
                variable.set(
                    False
                )

        def apply_filter() -> None:
            self.selected_plmn_conf_ids = {
                conf_id
                for conf_id, variable
                in checkbox_vars.items()
                if variable.get()
            }

            selected_count = len(
                self.selected_plmn_conf_ids
            )

            if selected_count:
                self.plmn_filter_label_var.set(
                    f"PLMN filter "
                    f"({selected_count})"
                )

            else:
                self.plmn_filter_label_var.set(
                    "PLMN filter"
                )

            self.refresh_combo_tree()

            dialog.destroy()

        button_frame = ttk.Frame(
            outer
        )

        button_frame.pack(
            fill="x",
            pady=(10, 0),
        )

        ttk.Button(
            button_frame,
            text="Reset",
            command=reset_filter,
        ).pack(
            side="left"
        )

        ttk.Button(
            button_frame,
            text="Apply filter",
            command=apply_filter,
        ).pack(
            side="right"
        )

        ttk.Button(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
        ).pack(
            side="right",
            padx=(0, 6),
        )

        dialog.update_idletasks()

        dialog.geometry(
            f"+{self.winfo_rootx() + 40}"
            f"+{self.winfo_rooty() + 40}"
        )

    def refresh_combo_tree(
        self,
        select_index: Optional[int] = None,
    ) -> None:
        for item in self.combo_tree.get_children():
            self.combo_tree.delete(item)

        query = self.search_var.get().strip()
        visible_indices: list[int] = []

        for index, combo in enumerate(
            self.document.combos
        ):
            if not self._combo_matches_filters(
                index,
                combo,
            ):
                continue

            visible_indices.append(index)

            self.combo_tree.insert(
                "",
                "end",
                iid=str(index),
                values=self._combo_row_values(
                    index,
                    combo,
                ),
            )

        if not self.document.combos:
            self.selected_combo_index = None
            self.clear_combo_editor()
            self.clear_component_editor()
            return

        if not visible_indices:
            self.selected_combo_index = None
            self.selected_component_index = None
            self.clear_combo_editor()
            self.clear_component_editor()

            active_filters = []

            if query:
                active_filters.append(
                    f'search="{query}"'
                )

            if self.selected_plmn_conf_ids:
                active_filters.append(
                    "PLMN mappings="
                    f"{len(self.selected_plmn_conf_ids)}"
                )

            if active_filters:
                self.status_var.set(
                    "No combinations match "
                    + ", ".join(active_filters)
                )
            else:
                self.status_var.set(
                    "No combinations available"
                )

            return

        if select_index is None:
            if (
                self.selected_combo_index
                in visible_indices
            ):
                select_index = (
                    self.selected_combo_index
                )
            else:
                select_index = visible_indices[0]

        elif select_index not in visible_indices:
            select_index = visible_indices[0]

        self.combo_tree.selection_set(
            str(select_index)
        )
        self.combo_tree.focus(
            str(select_index)
        )
        self.combo_tree.see(
            str(select_index)
        )

        self.selected_combo_index = select_index

        self.load_combo_editor()
        self.refresh_component_tree()

        active_filters = []

        if query:
            active_filters.append(
                f'search="{query}"'
            )

        if self.selected_plmn_conf_ids:
            active_filters.append(
                "PLMN mappings="
                f"{len(self.selected_plmn_conf_ids)}"
            )

        if active_filters:
            self.status_var.set(
                f"{len(visible_indices)} of "
                f"{len(self.document.combos)} "
                "combinations shown "
                f"({', '.join(active_filters)})"
            )
        else:
            self.status_var.set(
                f"{len(self.document.combos)} "
                "combinations loaded"
            )

    def refresh_component_tree(
        self,
        select_index: Optional[int] = None,
    ) -> None:
        self._close_component_cell_editor()

        for item in self.component_tree.get_children():
            self.component_tree.delete(
                item
            )

        combo = self.get_selected_combo()

        if combo is None:
            self.selected_component_index = None
            self.clear_component_editor()
            return

        for index, component in enumerate(
            combo.components
        ):
            dl_label = DL_VALUE_TO_LABEL.get(
                str(component.bwClassMimoDl),
                str(component.bwClassMimoDl),
            )

            ul_label = self._ul_label(
                component.bwClassMimoUl
            )

            self.component_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    index + 1,
                    component.band,
                    dl_label,
                    ul_label,
                ),
            )

        if not combo.components:
            self.selected_component_index = None
            self.clear_component_editor()
            return

        if select_index is None:
            if self.selected_component_index is None:
                select_index = 0
            else:
                select_index = (
                    self.selected_component_index
                )

        select_index = max(
            0,
            min(
                select_index,
                len(combo.components) - 1,
            ),
        )

        row_id = str(
            select_index
        )

        self.component_tree.selection_set(
            row_id
        )

        self.component_tree.focus(
            row_id
        )

        self.component_tree.see(
            row_id
        )

        self.selected_component_index = (
            select_index
        )

        # Keep the old StringVar values synchronized,
        # even though the old controls are no longer visible.
        self.load_component_editor()

    def on_combo_selected(
        self,
        _event=None,
    ) -> None:
        selection = self.combo_tree.selection()

        if not selection:
            return

        self.selected_combo_index = int(
            selection[0]
        )
        self.selected_component_index = None

        self.load_combo_editor()
        self.refresh_component_tree()

    def on_component_selected(
        self,
        _event=None,
    ) -> None:
        selection = self.component_tree.selection()

        if not selection:
            return

        self.selected_component_index = int(
            selection[0]
        )

        self.load_component_editor()

    def on_component_value_changed(
        self,
        _event=None,
    ) -> None:
        if self.get_selected_component() is None:
            return

        self.apply_component_fields(
            show_no_selection=False
        )

    def on_bcs_value_changed(
        self,
        _event=None,
    ) -> None:
        combo = self.get_selected_combo()

        if combo is None:
            return

        raw_value = BCS_LABEL_TO_VALUE.get(
            self.bcs_var.get()
        )

        if raw_value is None:
            return

        combo.bcs = int(raw_value)

        self.refresh_combo_tree(
            self.selected_combo_index
        )
        self.status_var.set("BCS updated")

    def get_selected_combo(self) -> Optional[Combo]:
        if self.selected_combo_index is None:
            return None

        if not (
            0
            <= self.selected_combo_index
            < len(self.document.combos)
        ):
            return None

        return self.document.combos[
            self.selected_combo_index
        ]

    def get_selected_component(
        self,
    ) -> Optional[Component]:
        combo = self.get_selected_combo()

        if (
            combo is None
            or self.selected_component_index is None
        ):
            return None

        if not (
            0
            <= self.selected_component_index
            < len(combo.components)
        ):
            return None

        return combo.components[
            self.selected_component_index
        ]

    def load_combo_editor(self) -> None:
        combo = self.get_selected_combo()

        if combo is None:
            self.clear_combo_editor()
            return

        self.bcs_var.set(
            BCS_VALUE_TO_LABEL.get(
                str(combo.bcs),
                str(combo.bcs),
            )
        )
        self.configMaskLow_var.set(
            str(combo.configMaskLow)
        )
        self.configMaskHigh_var.set(
            str(combo.configMaskHigh)
        )

    def clear_combo_editor(self) -> None:
        self.bcs_var.set(
            BCS_VALUE_TO_LABEL["2147483648"]
        )
        self.configMaskLow_var.set(
            "18445899642336968703"
        )
        self.configMaskHigh_var.set(
            "2097151"
        )

    def load_component_editor(self) -> None:
        component = self.get_selected_component()

        if component is None:
            self.clear_component_editor()
            return

        self.band_var.set(
            str(component.band)
        )
        self.dl_var.set(
            self._dropdown_label(
                component.bwClassMimoDl,
                DL_VALUE_TO_LABEL,
            )
        )
        self.ul_var.set(
            self._ul_label(component.bwClassMimoUl)
        )

    def clear_component_editor(self) -> None:
        self.band_var.set("1")
        self.dl_var.set(
            DL_VALUE_TO_LABEL["32768"]
        )
        self.ul_var.set(
            UL_VALUE_TO_LABEL["0"]
        )

    def add_combo(self) -> None:
        combo = Combo(
            components=[Component()],
            bcs=2147483648,
            configMaskLow=18445899642336968703,
            configMaskHigh=2097151,
        )

        self.document.combos.append(combo)

        index = len(self.document.combos) - 1
        self.selected_component_index = 0

        self.refresh_combo_tree(index)
        self.refresh_component_tree(0)

        self.status_var.set(
            "New combination added"
        )

    def _run_ul_generator(
        self,
        include_ulca: bool,
    ) -> None:
        if self.selected_combo_index is None:
            messagebox.showinfo(
                "No selection",
                "Select a combination first.",
            )
            return

        try:
            result = generate_ul_variants(
                self.document,
                self.selected_combo_index,
                include_ulca=include_ulca,

                # The manual Auto fill ULCA button allows A+A
                allow_fdd_aa_ulca=include_ulca,
                
                allow_tdd_aa_ulca=False,
                allow_fdd_tdd_ulca=False,
            )

        except ValueError as exc:
            messagebox.showinfo(
                "Cannot generate UL variants",
                str(exc),
            )
            return

        self.selected_component_index = None

        self.refresh_combo_tree(
            self.selected_combo_index
        )

        self.refresh_component_tree()

        if result.created_count == 0:
            messagebox.showinfo(
                "Nothing to add",
                result.message,
            )

        self.status_var.set(result.message)

    def auto_fill_ul_band(self) -> None:
        self._run_ul_generator(
            include_ulca=False
        )

    def auto_fill_ulca(self) -> None:
        self._run_ul_generator(
            include_ulca=True
        )

    def duplicate_combo(self) -> None:
        combo = self.get_selected_combo()

        if (
            combo is None
            or self.selected_combo_index is None
        ):
            return

        duplicate = copy_combo(combo)
        insert_at = self.selected_combo_index + 1

        self.document.combos.insert(
            insert_at,
            duplicate,
        )

        self.refresh_combo_tree(insert_at)
        self.refresh_component_tree(0)

        self.status_var.set(
            "Combination duplicated"
        )

    def delete_combo(self) -> None:
        if self.selected_combo_index is None:
            return

        if not messagebox.askyesno(
            "Delete combination",
            "Delete the selected CA combination?",
        ):
            return

        index = self.selected_combo_index

        del self.document.combos[index]

        self.selected_component_index = None

        if self.document.combos:
            next_index = min(
                index,
                len(self.document.combos) - 1,
            )
        else:
            next_index = None

        self.refresh_combo_tree(next_index)
        self.refresh_component_tree()

        self.status_var.set(
            "Combination deleted"
        )

    def move_combo(self, direction: int) -> None:
        if self.selected_combo_index is None:
            return

        old_index = self.selected_combo_index
        new_index = old_index + direction

        if not (
            0
            <= new_index
            < len(self.document.combos)
        ):
            return

        self.document.combos[
            old_index
        ], self.document.combos[
            new_index
        ] = (
            self.document.combos[new_index],
            self.document.combos[old_index],
        )

        self.refresh_combo_tree(new_index)

        self.status_var.set(
            "Combination moved"
        )

    def apply_combo_fields(self) -> None:
        combo = self.get_selected_combo()

        if combo is None:
            messagebox.showinfo(
                "No selection",
                "Select or add a combination first",
            )
            return

        try:
            raw_bcs = BCS_LABEL_TO_VALUE.get(
                self.bcs_var.get()
            )

            if raw_bcs is None:
                raise ValueError(
                    "Select a valid BCS option"
                )

            config_mask_low = self._int_value(
                self.configMaskLow_var.get(),
                "Conf ID 1",
            )
            config_mask_high = self._int_value(
                self.configMaskHigh_var.get(),
                "Conf ID 2",
            )

            if not (
                0
                <= config_mask_low
                <= 0xFFFFFFFFFFFFFFFF
            ):
                raise ValueError(
                    "Conf ID 1 must fit in uint64"
                )

            if not (
                0
                <= config_mask_high
                <= 0xFFFFFFFF
            ):
                raise ValueError(
                    "Conf ID 2 must fit in uint32"
                )

            combo.bcs = int(raw_bcs)
            combo.configMaskLow = config_mask_low
            combo.configMaskHigh = config_mask_high

        except ValueError as exc:
            messagebox.showerror(
                "Invalid value",
                str(exc),
            )
            return

        self.refresh_combo_tree(
            self.selected_combo_index
        )

        self.status_var.set(
            "Combination fields updated"
        )

    def open_conf_id_mapper(self) -> None:
        combo = self.get_selected_combo()

        if combo is None:
            messagebox.showinfo(
                "No selection",
                "Select or add a combination first",
            )
            return

        mapper = tk.Toplevel(self)
        mapper.title("conf_id mapping")
        mapper.transient(self)
        mapper.grab_set()
        mapper.resizable(False, False)

        outer = ttk.Frame(
            mapper,
            padding=12,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        value_frame = ttk.LabelFrame(
            outer,
            text="Calculated values",
            padding=8,
        )

        value_frame.pack(
            fill="x",
            pady=(0, 10),
        )

        low_value_var = tk.StringVar()
        high_value_var = tk.StringVar()

        ttk.Label(
            value_frame,
            text="Conf ID 1",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=3,
        )

        ttk.Entry(
            value_frame,
            textvariable=low_value_var,
            state="readonly",
            width=24,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(
            value_frame,
            text="Conf ID 2",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=3,
        )

        ttk.Entry(
            value_frame,
            textvariable=high_value_var,
            state="readonly",
            width=24,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=3,
        )

        value_frame.columnconfigure(
            1,
            weight=1,
        )

        ttk.Label(
            outer,
            text=(
                "conf_id 0 is hidden and always "
                "included as bit 0."
            ),
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        checkbox_frame = ttk.LabelFrame(
            outer,
            text="Select conf_id mapping",
            padding=8,
        )

        checkbox_frame.pack(
            fill="both",
            expand=True,
        )

        selected_ids = masks_to_conf_ids(
            combo.configMaskLow | 1,
            combo.configMaskHigh,
            include_bit_zero=True,
        )

        selected_ids.add(
            0
        )

        checkbox_vars: dict[
            int,
            tk.BooleanVar,
        ] = {}

        def current_selected_ids() -> set[int]:
            result = {
                conf_id
                for conf_id, variable
                in checkbox_vars.items()
                if variable.get()
            }

            # conf_id 0 is hidden but always enabled.
            result.add(
                0
            )

            return result

        def update_values(
            *_args,
        ) -> None:
            low_mask, high_mask = conf_ids_to_masks(
                current_selected_ids(),
                include_bit_zero=True,
            )

            low_value_var.set(
                str(low_mask)
            )

            high_value_var.set(
                str(high_mask)
            )

        visible_conf_ids = [
            conf_id
            for conf_id in sorted(
                self.conf_id_names
            )
            if conf_id != 0
        ]

        for display_index, conf_id in enumerate(
            visible_conf_ids
        ):
            row = display_index % 10
            column = display_index // 10

            variable = tk.BooleanVar(
                value=(
                    conf_id in selected_ids
                )
            )

            checkbox_vars[
                conf_id
            ] = variable

            variable.trace_add(
                "write",
                update_values,
            )

            ttk.Checkbutton(
                checkbox_frame,
                text=(
                    f"{self.conf_id_names[conf_id]} "
                    f"({conf_id})"
                ),
                variable=variable,
            ).grid(
                row=row,
                column=column,
                sticky="w",
                padx=(0, 12),
                pady=2,
            )

        for column in range(9):
            checkbox_frame.columnconfigure(
                column,
                weight=1,
            )

        def select_all() -> None:
            for variable in (
                checkbox_vars.values()
            ):
                variable.set(
                    True
                )

        def reset_mapping() -> None:
            for variable in (
                checkbox_vars.values()
            ):
                variable.set(
                    False
                )

        def apply_mapping() -> None:
            low_mask, high_mask = conf_ids_to_masks(
                current_selected_ids(),
                include_bit_zero=True,
            )

            combo.configMaskLow = low_mask
            combo.configMaskHigh = high_mask

            self.configMaskLow_var.set(
                str(low_mask)
            )

            self.configMaskHigh_var.set(
                str(high_mask)
            )

            self.refresh_combo_tree(
                self.selected_combo_index
            )

            self.status_var.set(
                "conf_id mapping applied"
            )

            mapper.destroy()

        button_frame = ttk.Frame(
            outer
        )

        button_frame.pack(
            fill="x",
            pady=(10, 0),
        )

        ttk.Button(
            button_frame,
            text="Reset",
            command=reset_mapping,
        ).pack(
            side="left"
        )

        ttk.Button(
            button_frame,
            text="Select all",
            command=select_all,
        ).pack(
            side="left",
            padx=(6, 0),
        )

        ttk.Button(
            button_frame,
            text="Apply mapping",
            command=apply_mapping,
        ).pack(
            side="right"
        )

        ttk.Button(
            button_frame,
            text="Cancel",
            command=mapper.destroy,
        ).pack(
            side="right",
            padx=(0, 6),
        )

        update_values()

        mapper.update_idletasks()

        mapper.geometry(
            f"+{self.winfo_rootx() + 40}"
            f"+{self.winfo_rooty() + 40}"
        )

    def add_component(
        self,
    ) -> None:
        combo = self.get_selected_combo()

        if combo is None:
            messagebox.showinfo(
                "No combination",
                "Add or select a combination first.",
                parent=self,
            )
            return

        ul_value = (
            S5300_UL_AUTO_VALUE
            if self._is_s5300_auto_ul_combo(combo)
            else 0
        )
        combo.components.append(
            Component(
                band=1,
                bwClassMimoDl=32768,
                bwClassMimoUl=ul_value,
            )
        )

        new_index = (
            len(combo.components) - 1
        )

        self.selected_component_index = (
            new_index
        )

        self.refresh_combo_tree(
            self.selected_combo_index
        )

        self.refresh_component_tree(
            new_index
        )

        self.status_var.set(
            "Band component added"
        )

        def open_new_band_editor() -> None:
            row_id = str(
                new_index
            )

            if self.component_tree.exists(
                row_id
            ):
                self._begin_component_cell_edit(
                    row_id=row_id,
                    column_id="#2",
                    component_index=new_index,
                )

        self.after_idle(
            open_new_band_editor
        )

    def apply_component_fields(
        self,
        show_no_selection: bool = True,
    ) -> None:
        combo = self.get_selected_combo()
        component = self.get_selected_component()
        component_index = self.selected_component_index

        if (
            combo is None
            or component is None
            or component_index is None
        ):
            if show_no_selection:
                messagebox.showinfo(
                    "No selection",
                    "Select a band component first",
                )
            return

        try:
            component.band = self._int_value(
                self.band_var.get(),
                "Band",
            )
            component.bwClassMimoDl = (
                self._dropdown_value(
                    self.dl_var.get(),
                    DL_LABEL_TO_VALUE,
                    "DL value",
                )
            )
            ul_value = self._dropdown_value(
                self.ul_var.get(),
                self._ul_label_to_value(),
                "UL value",
            )
        except ValueError as exc:
            messagebox.showerror(
                "Invalid value",
                str(exc),
            )
            return

        self._set_component_ul_value(
            combo,
            component_index,
            ul_value,
        )

        self.refresh_component_tree(
            self.selected_component_index
        )
        self.refresh_combo_tree(
            self.selected_combo_index
        )

        self.status_var.set(
            "Band component updated"
        )

    def delete_component(self) -> None:
        combo = self.get_selected_combo()

        if (
            combo is None
            or self.selected_component_index is None
        ):
            return

        index = self.selected_component_index

        del combo.components[index]

        self.selected_component_index = None

        if combo.components:
            next_index = min(
                index,
                len(combo.components) - 1,
            )
        else:
            next_index = None

        self.refresh_component_tree(next_index)
        self.refresh_combo_tree(
            self.selected_combo_index
        )

        self.status_var.set(
            "Band component deleted"
        )

    def move_component(
        self,
        direction: int,
    ) -> None:
        combo = self.get_selected_combo()

        if (
            combo is None
            or self.selected_component_index is None
        ):
            return

        old_index = self.selected_component_index
        new_index = old_index + direction

        if not (
            0
            <= new_index
            < len(combo.components)
        ):
            return

        combo.components[
            old_index
        ], combo.components[
            new_index
        ] = (
            combo.components[new_index],
            combo.components[old_index],
        )

        self.selected_component_index = new_index

        self.refresh_component_tree(new_index)
        self.refresh_combo_tree(
            self.selected_combo_index
        )

        self.status_var.set(
            "Band component moved"
        )

    def _choose_s5300_family(
        self,
        families: list[str],
    ) -> Optional[str]:
        if not families:
            return None
        if len(families) == 1:
            return families[0]

        dialog = tk.Toplevel(self)
        dialog.title("Select S5300 LTE CA family")
        dialog.transient(self)
        dialog.resizable(False, False)

        content = ttk.Frame(dialog, padding=12)
        content.pack(fill="both", expand=True)
        ttk.Label(
            content,
            text="LTE CA family",
        ).grid(row=0, column=0, sticky="w")

        family_var = tk.StringVar(value=families[0])
        selector = ttk.Combobox(
            content,
            textvariable=family_var,
            values=families,
            state="readonly",
            width=max(24, max(map(len, families)) + 2),
        )
        selector.grid(row=1, column=0, columnspan=2, pady=(6, 12))

        result: dict[str, Optional[str]] = {"family": None}

        def accept() -> None:
            result["family"] = family_var.get()
            dialog.destroy()

        ttk.Button(
            content,
            text="Cancel",
            command=dialog.destroy,
        ).grid(row=2, column=0, padx=(0, 6), sticky="e")
        ttk.Button(
            content,
            text="Open",
            command=accept,
        ).grid(row=2, column=1, sticky="w")

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.bind("<Return>", lambda _event: accept())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.wait_visibility()
        dialog.grab_set()
        selector.focus_set()
        self.wait_window(dialog)
        return result["family"]

    def _activate_s5300_document(
        self,
        document: ComboDocument,
        family: str,
        current_path: Path,
        bundle: Optional[S5300Bundle],
        conf_id_names: dict[int, str],
    ) -> None:
        self.document = document
        self.current_path = current_path
        self.s5300_bundle = bundle
        self.s5300_family = family
        self.conf_id_names = dict(conf_id_names)
        self.selected_combo_index = 0 if document.combos else None
        self.selected_component_index = None
        self.search_var.set("")
        self.selected_plmn_conf_ids.clear()
        self.plmn_filter_label_var.set("PLMN filter")
        self.refresh_all()
        self.title(
            "Shannon LTE CA editor -> "
            f"S5300 {family} ({current_path.name})"
        )

    def import_s5300_confseq_folder(self) -> None:
        directory = filedialog.askdirectory(
            title="Import S5300 carrierconfig confseq folder",
            mustexist=True,
        )
        if not directory:
            return

        source_dir = Path(directory)
        try:
            families = discover_s5300_families(source_dir)
        except (OSError, ParseError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Import failed", str(exc))
            return
        if not families:
            messagebox.showerror(
                "Import failed",
                "No complete S5300 LTE CA confseq family was found.",
            )
            return

        family = self._choose_s5300_family(families)
        if family is None:
            return

        try:
            bundle = load_s5300_bundle(source_dir, family)
        except (OSError, ParseError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Import failed", str(exc))
            return

        self._activate_s5300_document(
            bundle.document,
            family,
            source_dir,
            bundle,
            bundle.conf_id_names,
        )
        self.status_var.set(
            f"Imported {len(bundle.document.combos)} S5300 "
            f"combinations from {family}"
        )

    def export_s5300_confseq_folder(self) -> None:
        if self.s5300_bundle is None or self.s5300_family is None:
            messagebox.showinfo(
                "No S5300 confseq template",
                "Import the matching S5300 confseq folder before exporting "
                "raw confseq files.",
            )
            return

        directory = filedialog.askdirectory(
            title="Export modified S5300 confseq bundle",
            mustexist=True,
        )
        if not directory:
            return

        output_dir = Path(directory)
        try:
            same_directory = (
                output_dir.resolve() == self.s5300_bundle.source_dir.resolve()
            )
        except OSError:
            same_directory = False
        if same_directory and not messagebox.askyesno(
            "Overwrite source confseqs?",
            "This will replace the six source profiles for the selected "
            "family. Continue?",
        ):
            return

        try:
            written = export_s5300_bundle(
                self.s5300_bundle,
                self.document,
                output_dir,
            )
            exported_bundle = load_s5300_bundle(
                output_dir,
                self.s5300_family,
            )
        except (OSError, ParseError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Export failed", str(exc))
            return

        self.s5300_bundle = exported_bundle
        self.s5300_bundle.conf_id_names = dict(self.conf_id_names)
        self.current_path = output_dir
        self.title(
            "Shannon LTE CA editor -> "
            f"S5300 {self.s5300_family} ({output_dir.name})"
        )
        self.status_var.set(
            f"Exported and verified {len(written)} S5300 confseq profiles "
            f"to {output_dir}"
        )
        messagebox.showinfo(
            "Export complete",
            f"Exported and verified {len(written)} confseq profiles to:\n"
            f"{output_dir}",
        )

    def new_document(self) -> None:
        self.document = ComboDocument()
        self.current_path = None
        self.s5300_bundle = None
        self.s5300_family = None
        self.conf_id_names = dict(CONF_ID_NAMES)
        self.selected_combo_index = None
        self.selected_component_index = None

        self.search_var.set("")
        self.selected_plmn_conf_ids.clear()
        self.plmn_filter_label_var.set(
            "PLMN filter"
        )

        self.refresh_all()
        self.title(
            "Shannon LTE CA editor"
        )

    def import_decoded_txt(self) -> None:
        filename = filedialog.askopenfilename(
            title=(
                "Import LTE capability "
                "binary protobuf"
            ),
            filetypes=[
                (
                    "Binary protobuf",
                    "*.binarypb",
                ),
                (
                    "All files",
                    "*.*",
                ),
            ],
        )

        if not filename:
            return

        path = Path(filename)

        if path.suffix.lower() != ".binarypb":
            messagebox.showerror(
                "Invalid file",
                "Please select a .binarypb file.",
            )
            return

        try:
            self.document = parse_binary_document(
                path.read_bytes()
            )
        except (
            OSError,
            ParseError,
            ValueError,
            RuntimeError,
        ) as exc:
            messagebox.showerror(
                "Import failed",
                str(exc),
            )
            return

        self.s5300_bundle = None
        self.s5300_family = None
        self.conf_id_names = dict(CONF_ID_NAMES)
        self.current_path = path
        self.selected_combo_index = (
            0 if self.document.combos else None
        )
        self.selected_component_index = None

        self.search_var.set("")
        self.selected_plmn_conf_ids.clear()
        self.plmn_filter_label_var.set(
            "PLMN filter"
        )

        self.refresh_all()

        self.title(
            "Shannon LTE CA editor -> "
            f"{self.current_path.name}"
        )

        self.status_var.set(
            f"Imported {len(self.document.combos)} "
            "combinations from "
            f"{self.current_path.name}"
        )

    def import_text_file(self) -> None:
        filename = filedialog.askopenfilename(
            title="Import decoded LTE capability text",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not filename:
            return

        path = Path(filename)

        if path.suffix.lower() != ".txt":
            messagebox.showerror(
                "Invalid file",
                "Please select a .txt file.",
            )
            return

        try:
            self.document = parse_document(
                path.read_text(encoding="utf-8")
            )
        except (
            OSError,
            UnicodeError,
            ParseError,
            ValueError,
        ) as exc:
            messagebox.showerror(
                "Import failed",
                str(exc),
            )
            return

        self.s5300_bundle = None
        self.s5300_family = None
        self.conf_id_names = dict(CONF_ID_NAMES)
        self.current_path = path
        self.selected_combo_index = (
            0 if self.document.combos else None
        )
        self.selected_component_index = None

        self.search_var.set("")
        self.selected_plmn_conf_ids.clear()
        self.plmn_filter_label_var.set("PLMN filter")

        self.refresh_all()
        self.title(
            "Shannon LTE CA editor -> "
            f"{self.current_path.name}"
        )
        self.status_var.set(
            f"Imported {len(self.document.combos)} "
            "combinations from "
            f"{self.current_path.name}"
        )

    def save_text_file(self) -> None:
        if self.s5300_family is not None:
            messagebox.showinfo(
                "S5300 document loaded",
                "Use Export S5300 confseq folder for this document.",
            )
            return
        if self.current_path is not None:
            default_name = f"{self.current_path.stem}_mod.txt"
        else:
            default_name = "shannon_lte_capability.txt"

        filename = filedialog.asksaveasfilename(
            title="Export decoded LTE capability text",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not filename:
            return

        output_path = Path(filename)

        try:
            output_path.write_text(
                format_document(self.document),
                encoding="utf-8",
            )
        except (OSError, ValueError) as exc:
            messagebox.showerror(
                "Save failed",
                str(exc),
            )
            return

        self.status_var.set(
            f"Saved decoded text to {output_path}"
        )
        messagebox.showinfo(
            "Saved",
            "Decoded text saved as:\n"
            f"{output_path}",
        )

    def save_file(self) -> None:
        if self.s5300_family is not None:
            self.export_s5300_confseq_folder()
            return
        self.save_binary_file()

    def save_binary_file(self) -> None:
        if self.s5300_family is not None:
            messagebox.showinfo(
                "S5300 document loaded",
                "Use Export S5300 confseq folder for this document.",
            )
            return
        if self.current_path is None:
            messagebox.showinfo(
                "No file loaded",
                "Import a .binarypb file before saving.",
            )
            return

        default_name = (
            f"{self.current_path.stem}_mod.binarypb"
        )

        filename = filedialog.asksaveasfilename(
            title="Export binary protobuf",
            defaultextension=".binarypb",
            initialfile=default_name,
            filetypes=[
                (
                    "Binary protobuf",
                    "*.binarypb",
                ),
                (
                    "All files",
                    "*.*",
                ),
            ],
        )

        if not filename:
            return

        output_path = Path(filename)

        try:
            output_path.write_bytes(
                format_binary_document(
                    self.document
                )
            )
        except (
            OSError,
            ValueError,
            RuntimeError,
        ) as exc:
            messagebox.showerror(
                "Save failed",
                str(exc),
            )
            return

        self.status_var.set(
            "Saved binary protobuf to "
            f"{output_path}"
        )

        messagebox.showinfo(
            "Saved",
            "Binary protobuf saved as:\n"
            f"{output_path}",
        )

    def _write_to_path(
        self,
        path: Path,
    ) -> None:
        try:
            path.write_text(
                format_document(self.document),
                encoding="utf-8",
            )
        except OSError as exc:
            messagebox.showerror(
                "Save failed",
                str(exc),
            )
            return

        self.status_var.set(
            f"Saved to {path}"
        )

        messagebox.showinfo(
            "Saved",
            "Edited file saved as:\n"
            f"{path}",
        )

    def copy_exported_text(self) -> None:
        text = format_document(
            self.document
        )

        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

        self.status_var.set(
            "Exported text copied to clipboard"
        )

    def on_delete_combo_key(
        self,
        _event=None,
    ) -> str:
        self.delete_combo()
        return "break"

    def on_delete_component_key(
        self,
        _event=None,
    ) -> str:
        self.delete_component()
        return "break"


def main() -> None:
    app = ComboEditorApp()
    if "--smoke-test" in sys.argv:
        app.withdraw()
        app.update_idletasks()
        print("GUI_SMOKE_OK")
        app.destroy()
        return
    app.mainloop()


if __name__ == "__main__":
    main()
