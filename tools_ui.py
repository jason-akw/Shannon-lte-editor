import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from conf_id import (
    CONF_ID_NAMES,
    conf_ids_to_masks,
    masks_to_conf_ids,
)

from custom_utils import (
    apply_band_filter,
    generate_custom_combos,
    parse_band_list,
    parse_custom_combo,
    parse_exclusions,
)

from utils import (
    BCS_LABEL_TO_VALUE,
    BCS_VALUE_OPTIONS,
    ComboDocument,
    auto_fill_ul_bands,
    auto_fill_ulca,
    fix_validation_issues,
    validate_document,
)


ToolCallback = Optional[Callable[[str], None]]

HighlightCallback = Optional[
    Callable[[set[int]], None]
]

def _notify_changed(
    callback: ToolCallback,
    message: str,
) -> None:
    if callback is not None:
        callback(message)


def _center_window(
    window: tk.Toplevel,
    parent: tk.Misc,
) -> None:
    window.update_idletasks()

    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()

    parent_x = parent.winfo_rootx()
    parent_y = parent.winfo_rooty()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()

    x = parent_x + max(
        0,
        (parent_width - width) // 2,
    )

    y = parent_y + max(
        0,
        (parent_height - height) // 2,
    )

    window.geometry(
        f"+{x}+{y}"
    )


def _make_modal(
    window: tk.Toplevel,
    parent: tk.Misc,
) -> None:
    window.transient(parent)
    window.grab_set()

    window.protocol(
        "WM_DELETE_WINDOW",
        window.destroy,
    )

    _center_window(
        window,
        parent,
    )


class AutoGenerateCombosDialog(
    tk.Toplevel
):
    def __init__(
        self,
        parent: tk.Misc,
        document: ComboDocument,
        on_changed: ToolCallback = None,
        supports_auto_pcc: bool = False,
    ) -> None:
        super().__init__(parent)

        self.parent = parent
        self.document = document
        self.on_changed = on_changed
        self.supports_auto_pcc = supports_auto_pcc

        self.title(
            "Auto generate combos"
        )

        self.resizable(
            False,
            False,
        )

        self.theoretical_var = tk.StringVar(
            value=(
                "1+1+3+3+8B+28+32+40D+41"
            )
        )

        self.max_cc_var = tk.StringVar(
            value="5"
        )
        
        self.default_bcs_var = tk.StringVar(
            value=BCS_VALUE_OPTIONS[0][1]
        )

        self.allow_fdd_tdd_dl_var = (
            tk.BooleanVar(
                value=False
            )
        )

        self.ul_mode_var = tk.StringVar(
            value="disable"
        )

        self.use_auto_pcc_var = (
            tk.BooleanVar(
                value=False
            )
        )

        self.apply_ul_to_all_var = (
            tk.BooleanVar(
                value=False
            )
        )

        self.allow_fdd_tdd_ulca_var = (
            tk.BooleanVar(
                value=False
            )
        )
        
        self.allow_fdd_aa_ulca_var = (
            tk.BooleanVar(
                value=False
            )
        )

        self.allow_tdd_aa_ulca_var = (
            tk.BooleanVar(
                value=False
            )
        )

        self._build_ui()
        self._update_ul_state()

        _make_modal(
            self,
            parent,
        )

    def _build_ui(
        self,
    ) -> None:
        outer = ttk.Frame(
            self,
            padding=14,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        self._build_downlink_section(
            outer
        )

        self._build_uplink_section(
            outer
        )

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x",
            pady=(14, 0),
        )

        ttk.Button(
            buttons,
            text="Apply",
            command=self._apply,
        ).pack(
            side="right"
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=self.destroy,
        ).pack(
            side="right",
            padx=(0, 8),
        )

    def _build_downlink_section(
        self,
        parent: ttk.Widget,
    ) -> None:
        frame = ttk.LabelFrame(
            parent,
            text="Downlink settings",
            padding=10,
        )

        frame.pack(
            fill="x"
        )

        ttk.Label(
            frame,
            text="Theoretical combo",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=3,
        )

        ttk.Entry(
            frame,
            textvariable=(
                self.theoretical_var
            ),
            width=56,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(10, 0),
            pady=3,
        )

        options = ttk.Frame(
            frame
        )

        options.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )

        ttk.Label(
            options,
            text="Max CC",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Combobox(
            options,
            textvariable=self.max_cc_var,
            values=(
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
            ),
            state="readonly",
            width=5,
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(8, 20),
        )

        ttk.Checkbutton(
            options,
            text=(
                "Allow FDD+TDD combos"
            ),
            variable=(
                self.allow_fdd_tdd_dl_var
            ),
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        ttk.Label(
            options,
            text="Default BCS",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(8, 0),
        )

        ttk.Combobox(
            options,
            textvariable=self.default_bcs_var,
            values=[
                label
                for _value, label
                in BCS_VALUE_OPTIONS
            ],
            state="readonly",
            width=34,
        ).grid(
            row=1,
            column=1,
            columnspan=2,
            sticky="w",
            padx=(8, 0),
            pady=(8, 0),
        )

        ttk.Label(
            frame,
            text=(
                "Automatically respects HW limits such as allowing 28+20 for L+L, 24 spatial streams, B7+B38 uplink handling etc."
                " Exisiting combos are automatically detected and will not be duplicated"
            ),
            wraplength=620,
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 0),
        )

        frame.columnconfigure(
            1,
            weight=1,
        )

    def _build_uplink_section(
        self,
        parent: ttk.Widget,
    ) -> None:
        frame = ttk.LabelFrame(
            parent,
            text="Uplink settings",
            padding=10,
        )

        frame.pack(
            fill="x",
            pady=(12, 0),
        )

        modes = ttk.Frame(
            frame
        )

        modes.pack(
            fill="x"
        )

        ttk.Radiobutton(
            modes,
            text="No ULCA",
            variable=self.ul_mode_var,
            value="disable",
            command=self._update_ul_state,
        ).pack(
            side="left",
            padx=(0, 20),
        )

        ttk.Radiobutton(
            modes,
            text="Auto fill ULCA",
            variable=self.ul_mode_var,
            value="autofill",
            command=self._update_ul_state,
        ).pack(
            side="left"
        )

        self.auto_pcc_check = ttk.Checkbutton(
            frame,
            text=(
                "Use Auto PCC for single-PCC variants"
            ),
            variable=self.use_auto_pcc_var,
        )

        self.auto_pcc_check.pack(
            anchor="w",
            pady=(10, 0),
        )

        ttk.Checkbutton(
            frame,
            text=(
                "Apply UL generation to all document combos"
            ),
            variable=self.apply_ul_to_all_var,
        ).pack(
            anchor="w",
            pady=(6, 0),
        )

        ulca_options = ttk.Frame(
            frame
        )

        ulca_options.pack(
            fill="x",
            pady=(10, 0),
        )

        self.allow_fdd_aa_check = ttk.Checkbutton(
            ulca_options,
            text="Allow FDD A+A",
            variable=self.allow_fdd_aa_ulca_var,
        )

        self.allow_fdd_aa_check.pack(
            side="left",
            padx=(0, 18),
        )

        self.allow_tdd_aa_check = ttk.Checkbutton(
            ulca_options,
            text="Allow TDD A+A",
            variable=self.allow_tdd_aa_ulca_var,
        )

        self.allow_tdd_aa_check.pack(
            side="left",
            padx=(0, 18),
        )

        self.allow_mixed_ulca_check = ttk.Checkbutton(
            ulca_options,
            text="Allow TDD+FDD",
            variable=self.allow_fdd_tdd_ulca_var,
        )

        self.allow_mixed_ulca_check.pack(
            side="left"
        )

    def _update_ul_state(
        self,
    ) -> None:
        if self.supports_auto_pcc:
            self.auto_pcc_check.configure(
                state="normal"
            )
        else:
            self.use_auto_pcc_var.set(False)
            self.auto_pcc_check.configure(
                state="disabled"
            )

        controls = (
            self.allow_fdd_aa_check,
            self.allow_tdd_aa_check,
            self.allow_mixed_ulca_check,
        )

        if (
            self.ul_mode_var.get()
            == "autofill"
        ):
            for control in controls:
                control.configure(
                    state="normal"
                )

        else:
            self.allow_fdd_aa_ulca_var.set(
                False
            )

            self.allow_tdd_aa_ulca_var.set(
                False
            )

            self.allow_fdd_tdd_ulca_var.set(
                False
            )

            for control in controls:
                control.configure(
                    state="disabled"
                )

    def _apply(self) -> None:
        try:
            theoretical = parse_custom_combo(self.theoretical_var.get())

            try:
                max_cc = int(self.max_cc_var.get())
            except ValueError as exc:
                raise ValueError("Max CC must be an integer between 2 and 7.") from exc

            selected_bcs_label = self.default_bcs_var.get()

            try:
                selected_bcs = int(BCS_LABEL_TO_VALUE[selected_bcs_label])
            except KeyError as exc:
                raise ValueError("Select a valid default BCS.") from exc

            (
                added_dl,
                skipped_dl,
                involved_dl_signatures,
            ) = generate_custom_combos(
                self.document,
                theoretical,
                max_cc,
                self.allow_fdd_tdd_dl_var.get(),
                default_bcs=selected_bcs,
            )

            summary = [
                f"Custom DL combos added: {added_dl}",
                f"Existing DL combos skipped: {skipped_dl}",
            ]

            ul_mode = self.ul_mode_var.get()
            use_auto_pcc = (
                self.supports_auto_pcc
                and self.use_auto_pcc_var.get()
            )
            target_dl_signatures = (
                None
                if self.apply_ul_to_all_var.get()
                else involved_dl_signatures
            )

            if ul_mode == "disable":
                added_ul = auto_fill_ul_bands(
                    self.document,
                    use_auto_pcc=use_auto_pcc,
                    supports_auto_pcc=self.supports_auto_pcc,
                    target_dl_signatures=target_dl_signatures,
                )

                if use_auto_pcc:
                    summary.append(
                        f"Auto PCC or fallback UL variants added: {added_ul}"
                    )
                else:
                    summary.append(f"Single-band Class-A UL variants added: {added_ul}")

            elif ul_mode == "autofill":
                added_ul = auto_fill_ulca(
                    self.document,
                    allow_fdd_aa_ulca=self.allow_fdd_aa_ulca_var.get(),
                    allow_tdd_aa_ulca=self.allow_tdd_aa_ulca_var.get(),
                    allow_fdd_tdd_ulca=self.allow_fdd_tdd_ulca_var.get(),
                    use_auto_pcc=use_auto_pcc,
                    supports_auto_pcc=self.supports_auto_pcc,
                    target_dl_signatures=target_dl_signatures,
                )

                summary.append(f"UL and ULCA variants added: {added_ul}")

        except (RuntimeError, ValueError) as exc:
            messagebox.showerror("Auto generation failed", str(exc), parent=self)
            return

        summary_text = "\n".join(summary)
        _notify_changed(self.on_changed, summary_text)
        messagebox.showinfo("Auto generation complete", summary_text, parent=self)

        self.destroy()

class ComboPruningDialog(
    tk.Toplevel
):
    def __init__(
        self,
        parent: tk.Misc,
        document: ComboDocument,
        on_changed: ToolCallback = None,
    ) -> None:
        super().__init__(parent)

        self.parent = parent
        self.document = document
        self.on_changed = on_changed

        self.title(
            "Combo pruning"
        )

        self.resizable(
            False,
            False,
        )

        self.allowed_bands_var = tk.StringVar(
            value="1, 3, 8, 28, 40, 41"
        )

        self.exclusions_var = tk.StringVar(
            value=(
                "1+1, 3+3, 40+40, 41+41, 1C, 3C, 41D"
            )
        )

        self._build_ui()

        _make_modal(
            self,
            parent,
        )

    def _build_ui(
        self,
    ) -> None:
        outer = ttk.Frame(
            self,
            padding=14,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        frame = ttk.LabelFrame(
            outer,
            text="Band settings",
            padding=10,
        )

        frame.pack(
            fill="x"
        )

        ttk.Label(
            frame,
            text="Include LTE bands",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=4,
        )

        ttk.Entry(
            frame,
            textvariable=(
                self.allowed_bands_var
            ),
            width=58,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(10, 0),
            pady=4,
        )

        ttk.Label(
            frame,
            text="Exclude intra-band CA",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=4,
        )

        ttk.Entry(
            frame,
            textvariable=(
                self.exclusions_var
            ),
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(10, 0),
            pady=4,
        )

        ttk.Label(
            frame,
            text=(
                "Example: If you input 40D, 40C and 40A will be kept. If you input 3+3, any combo with 3+3 will be removed."
            ),
            wraplength=620,
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 0),
        )

        frame.columnconfigure(
            1,
            weight=1,
        )

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x",
            pady=(14, 0),
        )

        ttk.Button(
            buttons,
            text="Apply",
            command=self._apply,
        ).pack(
            side="right"
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=self.destroy,
        ).pack(
            side="right",
            padx=(0, 8),
        )
        
        ttk.Button(
            buttons,
            text="Delete all combos",
            command=self._clear_all_combos,
        ).pack(
            side="left"
        )
        
    def _clear_all_combos(self) -> None:
        combo_count = len(self.document.combos)

        if combo_count == 0:
            messagebox.showinfo(
                "No combos",
                "There are no combos to delete.",
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Delete all combos",
            (
                f"This will permanently remove all "
                f"{combo_count} loaded combos.\n\n"
                "This cannot be undone unless you reload "
                "the original.\n\n"
                "Are you sure?"
            ),
            parent=self,
        )

        if not confirmed:
            return

        self.document.combos.clear()

        message = (
            f"All {combo_count} combos were deleted."
        )

        _notify_changed(
            self.on_changed,
            message,
        )

        messagebox.showinfo(
            "All combos deleted",
            message,
            parent=self,
        )

        self.destroy()

    def _apply(
        self,
    ) -> None:
        try:
            allowed_bands = parse_band_list(
                self.allowed_bands_var.get()
            )

            exclusions = parse_exclusions(
                self.exclusions_var.get()
            )

            removed = apply_band_filter(
                self.document,
                allowed_bands,
                exclusions,
            )

        except ValueError as exc:
            messagebox.showerror(
                "Combo pruning failed",
                str(exc),
                parent=self,
            )
            return

        message = (
            "Combos removed: "
            f"{removed}"
        )

        _notify_changed(
            self.on_changed,
            message,
        )

        messagebox.showinfo(
            "Combo pruning complete",
            message,
            parent=self,
        )

        self.destroy()


class ConfIdDialog(
    tk.Toplevel
):
    def __init__(
        self,
        parent: tk.Misc,
        document: ComboDocument,
        on_changed: ToolCallback = None,
        conf_id_names: Optional[dict[int, str]] = None,
    ) -> None:
        super().__init__(parent)

        self.parent = parent
        self.document = document
        self.conf_id_names = dict(conf_id_names or CONF_ID_NAMES)
        self.on_changed = on_changed

        self.title(
            "Apply conf_id to combos"
        )

        self.resizable(
            False,
            False,
        )

        initial_low = 1
        initial_high = 0

        if document.combos:
            initial_low = (
                document.combos[
                    0
                ].configMaskLow
                | 1
            )

            initial_high = (
                document.combos[
                    0
                ].configMaskHigh
            )

        self.conf_low_var = tk.StringVar(
            value=str(initial_low)
        )

        self.conf_high_var = tk.StringVar(
            value=str(initial_high)
        )

        self.apply_all_var = tk.BooleanVar(
            value=True
        )

        self.apply_bands_var = tk.BooleanVar(
            value=False
        )

        self.band_list_var = tk.StringVar(
            value="1,3,8,28"
        )

        self._build_ui()
        self._update_target_state()

        _make_modal(
            self,
            parent,
        )

    def _build_ui(
        self,
    ) -> None:
        outer = ttk.Frame(
            self,
            padding=14,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        values_frame = ttk.LabelFrame(
            outer,
            text="conf_id values",
            padding=10,
        )

        values_frame.pack(
            fill="x"
        )

        ttk.Label(
            values_frame,
            text="conf_id 0 to 63",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=3,
        )

        ttk.Entry(
            values_frame,
            textvariable=(
                self.conf_low_var
            ),
            width=28,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(10, 0),
            pady=3,
        )

        ttk.Label(
            values_frame,
            text="conf_id 64 to 95",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=3,
        )

        ttk.Entry(
            values_frame,
            textvariable=(
                self.conf_high_var
            ),
            width=28,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(10, 0),
            pady=3,
        )

        ttk.Button(
            values_frame,
            text="Find conf_id mapping",
            command=self._open_mapper,
        ).grid(
            row=0,
            column=2,
            rowspan=2,
            sticky="nsew",
            padx=(10, 0),
            pady=3,
        )

        values_frame.columnconfigure(
            1,
            weight=1,
        )

        targets_frame = ttk.LabelFrame(
            outer,
            text="Apply to",
            padding=10,
        )

        targets_frame.pack(
            fill="x",
            pady=(12, 0),
        )

        ttk.Checkbutton(
            targets_frame,
            text=(
                "Apply conf_id to all combos"
            ),
            variable=self.apply_all_var,
            command=self._select_all_mode,
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=3,
        )

        ttk.Checkbutton(
            targets_frame,
            text=(
                "Apply conf_id to combos with the following bands:"
            ),
            variable=self.apply_bands_var,
            command=self._select_band_mode,
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=3,
        )

        ttk.Label(
            targets_frame,
            text="LTE bands",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=3,
        )

        self.band_entry = ttk.Entry(
            targets_frame,
            textvariable=(
                self.band_list_var
            ),
            width=44,
        )

        self.band_entry.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(10, 0),
            pady=3,
        )

        targets_frame.columnconfigure(
            1,
            weight=1,
        )

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x",
            pady=(14, 0),
        )

        ttk.Button(
            buttons,
            text="Apply",
            command=self._apply,
        ).pack(
            side="right"
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=self.destroy,
        ).pack(
            side="right",
            padx=(0, 8),
        )

    def _select_all_mode(
        self,
    ) -> None:
        if self.apply_all_var.get():
            self.apply_bands_var.set(
                False
            )

        elif not self.apply_bands_var.get():
            self.apply_all_var.set(
                True
            )

        self._update_target_state()

    def _select_band_mode(
        self,
    ) -> None:
        if self.apply_bands_var.get():
            self.apply_all_var.set(
                False
            )

        elif not self.apply_all_var.get():
            self.apply_bands_var.set(
                True
            )

        self._update_target_state()

    def _update_target_state(
        self,
    ) -> None:
        state = (
            "normal"
            if self.apply_bands_var.get()
            else "disabled"
        )

        self.band_entry.configure(
            state=state
        )

    @staticmethod
    def _parse_uint(
        text: str,
        name: str,
        maximum: int,
    ) -> int:
        try:
            value = int(
                text.strip(),
                10,
            )

        except ValueError as exc:
            raise ValueError(
                f"{name} must be a "
                "decimal integer."
            ) from exc

        if not 0 <= value <= maximum:
            raise ValueError(
                f"{name} is outside its "
                "valid range."
            )

        return value

    def _open_mapper(
        self,
    ) -> None:
        try:
            low = self._parse_uint(
                self.conf_low_var.get(),
                "conf_id 0 to 63",
                0xFFFFFFFFFFFFFFFF,
            )

            high = self._parse_uint(
                self.conf_high_var.get(),
                "conf_id 64 to 95",
                0xFFFFFFFF,
            )

        except ValueError as exc:
            messagebox.showerror(
                "Invalid conf_id",
                str(exc),
                parent=self,
            )
            return

        low |= 1

        mapper = tk.Toplevel(
            self
        )

        mapper.title(
            "Select conf_id PLMNs"
        )

        mapper.resizable(
            False,
            False,
        )

        outer = ttk.Frame(
            mapper,
            padding=12,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        values_frame = ttk.LabelFrame(
            outer,
            text="Calculated values",
            padding=8,
        )

        values_frame.pack(
            fill="x",
            pady=(0, 10),
        )

        calculated_low_var = tk.StringVar()
        calculated_high_var = tk.StringVar()

        ttk.Label(
            values_frame,
            text="conf_id 0 to 63",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=2,
        )

        ttk.Entry(
            values_frame,
            textvariable=(
                calculated_low_var
            ),
            state="readonly",
            width=24,
        ).grid(
            row=0,
            column=1,
            padx=(8, 0),
            pady=2,
        )

        ttk.Label(
            values_frame,
            text="conf_id 64 to 95",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=2,
        )

        ttk.Entry(
            values_frame,
            textvariable=(
                calculated_high_var
            ),
            state="readonly",
            width=24,
        ).grid(
            row=1,
            column=1,
            padx=(8, 0),
            pady=2,
        )

        ttk.Label(
            outer,
            text=(
                "Default conf_id 0 is "
                "always included."
            ),
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        checks = ttk.LabelFrame(
            outer,
            text="Select conf_id mapping",
            padding=8,
        )

        checks.pack(
            fill="both",
            expand=True,
        )

        selected_ids = masks_to_conf_ids(
            low,
            high,
            include_bit_zero=True,
        )

        selected_ids.add(
            0
        )

        variables: dict[
            int,
            tk.BooleanVar,
        ] = {}

        def selected_conf_ids() -> set[int]:
            result = {
                conf_id
                for conf_id, variable
                in variables.items()
                if variable.get()
            }

            result.add(
                0
            )

            return result

        def update_values(
            *_args,
        ) -> None:
            (
                calculated_low,
                calculated_high,
            ) = conf_ids_to_masks(
                selected_conf_ids(),
                include_bit_zero=True,
            )

            calculated_low_var.set(
                str(calculated_low)
            )

            calculated_high_var.set(
                str(calculated_high)
            )

        visible_ids = [
            conf_id
            for conf_id
            in sorted(self.conf_id_names)
            if conf_id != 0
        ]

        row_count = 10

        for position, conf_id in enumerate(
            visible_ids
        ):
            row = (
                position % row_count
            )

            column = (
                position // row_count
            )

            variable = tk.BooleanVar(
                value=(
                    conf_id
                    in selected_ids
                )
            )

            variable.trace_add(
                "write",
                update_values,
            )

            variables[
                conf_id
            ] = variable

            ttk.Checkbutton(
                checks,
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

        def select_all() -> None:
            for variable in variables.values():
                variable.set(
                    True
                )

        def reset_mapping() -> None:
            for variable in variables.values():
                variable.set(
                    False
                )

        def apply_mapper_values() -> None:
            self.conf_low_var.set(
                calculated_low_var.get()
            )

            self.conf_high_var.set(
                calculated_high_var.get()
            )

            mapper.destroy()

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x",
            pady=(10, 0),
        )

        ttk.Button(
            buttons,
            text="Reset",
            command=reset_mapping,
        ).pack(
            side="left"
        )

        ttk.Button(
            buttons,
            text="Select all",
            command=select_all,
        ).pack(
            side="left",
            padx=(6, 0),
        )

        ttk.Button(
            buttons,
            text="Apply",
            command=apply_mapper_values,
        ).pack(
            side="right"
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=mapper.destroy,
        ).pack(
            side="right",
            padx=(0, 8),
        )

        update_values()

        _make_modal(
            mapper,
            self,
        )

    def _apply(
        self,
    ) -> None:
        try:
            low = self._parse_uint(
                self.conf_low_var.get(),
                "conf_id 0 to 63",
                0xFFFFFFFFFFFFFFFF,
            )

            high = self._parse_uint(
                self.conf_high_var.get(),
                "conf_id 64 to 95",
                0xFFFFFFFF,
            )

            low |= 1

            selected_bands: set[int] = set()

            if self.apply_bands_var.get():
                selected_bands = parse_band_list(
                    self.band_list_var.get()
                )

            changed_count = 0

            for combo in self.document.combos:
                should_apply = (
                    self.apply_all_var.get()
                )

                if self.apply_bands_var.get():
                    should_apply = any(
                        component.band
                        in selected_bands
                        for component
                        in combo.components
                    )

                if not should_apply:
                    continue

                combo.configMaskLow = low
                combo.configMaskHigh = high
                changed_count += 1

        except ValueError as exc:
            messagebox.showerror(
                "Apply conf_id failed",
                str(exc),
                parent=self,
            )
            return

        message = (
            "conf_id updated on combos: "
            f"{changed_count}"
        )

        _notify_changed(
            self.on_changed,
            message,
        )

        messagebox.showinfo(
            "conf_id applied",
            message,
            parent=self,
        )

        self.destroy()


def open_auto_generate_dialog(
    parent: tk.Misc,
    document: ComboDocument,
    on_changed: ToolCallback = None,
    supports_auto_pcc: bool = False,
) -> AutoGenerateCombosDialog:
    return AutoGenerateCombosDialog(
        parent,
        document,
        on_changed,
        supports_auto_pcc,
    )


def open_combo_pruning_dialog(
    parent: tk.Misc,
    document: ComboDocument,
    on_changed: ToolCallback = None,
) -> ComboPruningDialog:
    return ComboPruningDialog(
        parent,
        document,
        on_changed,
    )


def open_conf_id_dialog(
    parent: tk.Misc,
    document: ComboDocument,
    on_changed: ToolCallback = None,
    conf_id_names: Optional[dict[int, str]] = None,
) -> ConfIdDialog:
    return ConfIdDialog(
        parent=parent,
        document=document,
        on_changed=on_changed,
        conf_id_names=conf_id_names,
    )

class ValidationDialog(
    tk.Toplevel
):
    def __init__(
        self,
        parent: tk.Misc,
        document: ComboDocument,
        on_changed: ToolCallback = None,
        on_highlight: HighlightCallback = None,
        supports_auto_pcc: bool = False,
    ) -> None:
        super().__init__(parent)

        self.parent = parent
        self.document = document
        self.on_changed = on_changed
        self.on_highlight = on_highlight
        self.supports_auto_pcc = supports_auto_pcc

        self.title(
            "Validate combos"
        )

        self.geometry(
            "760x520"
        )

        self.minsize(
            620,
            400,
        )

        self.report = validate_document(
            self.document
        )

        self._build_ui()
        self._render_report()

        _make_modal(
            self,
            parent,
        )

    def _build_ui(
        self,
    ) -> None:
        outer = ttk.Frame(
            self,
            padding=14,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        self.heading_var = tk.StringVar()

        ttk.Label(
            outer,
            textvariable=self.heading_var,
            font=(
                "TkDefaultFont",
                11,
                "bold",
            ),
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        text_frame = ttk.Frame(
            outer
        )

        text_frame.pack(
            fill="both",
            expand=True,
        )

        self.report_text = tk.Text(
            text_frame,
            wrap="word",
            state="disabled",
            height=20,
        )

        scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.report_text.yview,
        )

        self.report_text.configure(
            yscrollcommand=scrollbar.set
        )

        self.report_text.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x",
            pady=(12, 0),
        )

        self.highlight_button = ttk.Button(
            buttons,
            text="Highlight issue(s)",
            command=self._highlight,
        )

        self.highlight_button.pack(
            side="left"
        )

        self.fix_button = ttk.Button(
            buttons,
            text="Fix automatically",
            command=self._fix,
        )

        self.fix_button.pack(
            side="left",
            padx=(8, 0),
        )

        ttk.Button(
            buttons,
            text="Close",
            command=self.destroy,
        ).pack(
            side="right"
        )

    def _render_report(
        self,
    ) -> None:
        self.report_text.configure(
            state="normal"
        )

        self.report_text.delete(
            "1.0",
            "end"
        )

        if self.report.is_valid:
            self.heading_var.set(
                "No issue(s) found"
            )

            self.report_text.insert(
                "end",
                (
                ),
            )

            self.highlight_button.configure(
                state="disabled"
            )

            self.fix_button.configure(
                state="disabled"
            )

        else:
            self.heading_var.set(
                f"Found {len(self.report.issues)} issue(s)"
            )

            for issue in self.report.issues:
                fix_status = (
                    "Can be fixed automatically"
                    if issue.fixable
                    else "Manual fix required"
                )

                self.report_text.insert(
                    "end",
                    f"• {issue.message}\n",
                )

                self.report_text.insert(
                    "end",
                    f"  {fix_status}\n\n",
                )

            self.highlight_button.configure(
                state=(
                    "normal"
                    if self.on_highlight
                    else "disabled"
                )
            )

            has_fixable = any(
                issue.fixable
                for issue in self.report.issues
            )

            self.fix_button.configure(
                state=(
                    "normal"
                    if has_fixable
                    else "disabled"
                )
            )

        self.report_text.configure(
            state="disabled"
        )

    def _highlight(
        self,
    ) -> None:
        if self.on_highlight is None:
            return

        self.on_highlight(
            self.report.affected_indices
        )

    def _fix(
        self,
    ) -> None:
        confirmed = messagebox.askyesno(
            "Fix validation issues",
            (
                "Automatically repair all supported "
                "issues?\n\n"
                "Low-band conflicts and combinations "
                "with no legal uplink band will remain "
                "for manual review."
            ),
            parent=self,
        )

        if not confirmed:
            return

        results = fix_validation_issues(
            self.document,
            self.report,
            supports_auto_pcc=self.supports_auto_pcc,
        )

        summary = (
            "Automatic validation fixes applied:\n\n"
            f"Duplicates removed: "
            f"{results['duplicates_removed']}\n"
            f"Invalid UL assignments removed: "
            f"{results['invalid_ul_removed']}\n"
            f"Missing UL assignments filled: "
            f"{results['missing_ul_filled']}\n"
            f"UL classes repaired: "
            f"{results['ul_classes_repaired']}\n"
            f"Low-band 4×4 MIMO repaired: "
            f"{results['low_band_mimo_repaired']}\n"
            f"MIMO configurations downgraded: "
            f"{results['mimo_downgrades']}\n"
            f"Manual-review issues remaining: "
            f"{results['unfixable']}"
        )

        _notify_changed(
            self.on_changed,
            summary,
        )

        self.report = validate_document(
            self.document
        )

        self._render_report()

        messagebox.showinfo(
            "Automatic fixes complete",
            summary,
            parent=self,
        )

def run_validate_tool(
    parent: tk.Misc,
    document: ComboDocument,
    on_changed: ToolCallback = None,
    on_highlight: HighlightCallback = None,
    supports_auto_pcc: bool = False,
) -> Optional[ValidationDialog]:
    report = validate_document(
        document
    )

    if report.is_valid:
        messagebox.showinfo(
            "Validate combos",
            "No issue(s) found",
            parent=parent,
        )
        return None

    return ValidationDialog(
        parent=parent,
        document=document,
        on_changed=on_changed,
        on_highlight=on_highlight,
        supports_auto_pcc=supports_auto_pcc,
    )
