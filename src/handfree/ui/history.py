"""
History Panel Component

Provides a scrollable panel showing transcription history with copy functionality.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional

from handfree.storage.history_store import TranscriptionRecord


class HistoryPanel:
    """
    A toggleable panel showing transcription history.

    Displays recent transcriptions in a scrollable list with copy functionality.
    """

    # UI configuration
    WINDOW_WIDTH = 400
    WINDOW_HEIGHT = 500
    ENTRY_PADDING = 8
    TEXT_COLOR = "#FFFFFF"
    BG_COLOR = "#1E1E1E"
    ENTRY_BG = "#2D2D2D"
    HOVER_BG = "#3D3D3D"
    TIMESTAMP_COLOR = "#888888"
    DURATION_COLOR = "#666666"

    def __init__(
        self,
        root: tk.Tk,
        on_copy: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize history panel.

        Args:
            root: Parent tkinter window
            on_copy: Callback when text is copied (receives copied text)
        """
        self._root = root
        self._on_copy = on_copy
        self._visible = False
        self._entries: List[TranscriptionRecord] = []

        # Create toplevel window
        self._window = tk.Toplevel(root)
        self._window.withdraw()  # Start hidden
        self._window.title("HandFree History")
        self._window.configure(bg=self.BG_COLOR)

        # Set window size and position (right side of screen)
        self._position_window()

        # Make it stay on top
        self._window.attributes("-topmost", True)

        # Handle window close button
        self._window.protocol("WM_DELETE_WINDOW", self.hide)

        # Create UI components
        self._create_widgets()

    def _position_window(self) -> None:
        """Position window on right side of screen."""
        screen_width = self._window.winfo_screenwidth()
        screen_height = self._window.winfo_screenheight()

        x = screen_width - self.WINDOW_WIDTH - 20
        y = (screen_height - self.WINDOW_HEIGHT) // 2

        self._window.geometry(
            f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{x}+{y}"
        )

    def _create_widgets(self) -> None:
        """Create the panel UI components."""
        # Header frame
        header_frame = tk.Frame(self._window, bg=self.BG_COLOR)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # Title label
        title_label = tk.Label(
            header_frame,
            text="Transcription History",
            font=("Arial", 14, "bold"),
            fg=self.TEXT_COLOR,
            bg=self.BG_COLOR
        )
        title_label.pack(side=tk.LEFT)

        # Entry count label
        self._count_label = tk.Label(
            header_frame,
            text="",
            font=("Arial", 10),
            fg=self.TIMESTAMP_COLOR,
            bg=self.BG_COLOR
        )
        self._count_label.pack(side=tk.RIGHT)

        # Create scrollable frame
        self._create_scrollable_frame()

    def _create_scrollable_frame(self) -> None:
        """Create a scrollable container for history entries."""
        # Container frame
        container = tk.Frame(self._window, bg=self.BG_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Canvas for scrolling
        self._canvas = tk.Canvas(
            container,
            bg=self.BG_COLOR,
            highlightthickness=0
        )

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            container,
            orient=tk.VERTICAL,
            command=self._canvas.yview
        )

        # Scrollable frame inside canvas
        self._scrollable_frame = tk.Frame(self._canvas, bg=self.BG_COLOR)

        # Configure scrolling
        self._scrollable_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )

        self._canvas_window = self._canvas.create_window(
            (0, 0),
            window=self._scrollable_frame,
            anchor="nw"
        )

        self._canvas.configure(yscrollcommand=scrollbar.set)

        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind mouse wheel scrolling
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Update canvas window width when resized
        self._canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event) -> None:
        """Update canvas window width to match canvas."""
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel scrolling."""
        if self._visible:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _create_entry_widget(
        self,
        parent: tk.Frame,
        record: TranscriptionRecord
    ) -> tk.Frame:
        """
        Create a widget for a single history entry.

        Args:
            parent: Parent frame
            record: The transcription record to display

        Returns:
            The created entry frame
        """
        # Entry frame
        entry_frame = tk.Frame(
            parent,
            bg=self.ENTRY_BG,
            padx=self.ENTRY_PADDING,
            pady=self.ENTRY_PADDING
        )
        entry_frame.pack(fill=tk.X, pady=2)

        # Header row with timestamp and duration
        header_frame = tk.Frame(entry_frame, bg=self.ENTRY_BG)
        header_frame.pack(fill=tk.X)

        # Timestamp
        timestamp_str = record.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        timestamp_label = tk.Label(
            header_frame,
            text=timestamp_str,
            font=("Arial", 9),
            fg=self.TIMESTAMP_COLOR,
            bg=self.ENTRY_BG
        )
        timestamp_label.pack(side=tk.LEFT)

        # Duration (if available)
        if record.duration_seconds is not None:
            duration_str = f"{record.duration_seconds:.1f}s"
            duration_label = tk.Label(
                header_frame,
                text=duration_str,
                font=("Arial", 9),
                fg=self.DURATION_COLOR,
                bg=self.ENTRY_BG
            )
            duration_label.pack(side=tk.LEFT, padx=(10, 0))

        # Copy button
        copy_btn = tk.Button(
            header_frame,
            text="Copy",
            font=("Arial", 8),
            command=lambda: self._copy_text(record.text),
            bg="#4A4A4A",
            fg=self.TEXT_COLOR,
            activebackground="#5A5A5A",
            activeforeground=self.TEXT_COLOR,
            relief=tk.FLAT,
            padx=6,
            pady=1
        )
        copy_btn.pack(side=tk.RIGHT)

        # Text content (truncated if too long)
        display_text = record.text
        if len(display_text) > 200:
            display_text = display_text[:200] + "..."

        text_label = tk.Label(
            entry_frame,
            text=display_text,
            font=("Arial", 11),
            fg=self.TEXT_COLOR,
            bg=self.ENTRY_BG,
            wraplength=self.WINDOW_WIDTH - 50,
            justify=tk.LEFT,
            anchor="w"
        )
        text_label.pack(fill=tk.X, pady=(5, 0))

        # Hover effects
        def on_enter(e):
            entry_frame.configure(bg=self.HOVER_BG)
            header_frame.configure(bg=self.HOVER_BG)
            timestamp_label.configure(bg=self.HOVER_BG)
            text_label.configure(bg=self.HOVER_BG)
            if record.duration_seconds is not None:
                duration_label.configure(bg=self.HOVER_BG)

        def on_leave(e):
            entry_frame.configure(bg=self.ENTRY_BG)
            header_frame.configure(bg=self.ENTRY_BG)
            timestamp_label.configure(bg=self.ENTRY_BG)
            text_label.configure(bg=self.ENTRY_BG)
            if record.duration_seconds is not None:
                duration_label.configure(bg=self.ENTRY_BG)

        entry_frame.bind("<Enter>", on_enter)
        entry_frame.bind("<Leave>", on_leave)

        return entry_frame

    def _copy_text(self, text: str) -> None:
        """Copy text to clipboard and call callback."""
        try:
            self._root.clipboard_clear()
            self._root.clipboard_append(text)
            self._root.update()

            if self._on_copy:
                self._on_copy(text)
        except tk.TclError:
            pass

    def load_entries(self, entries: List[TranscriptionRecord]) -> None:
        """
        Load entries into the history panel.

        Args:
            entries: List of TranscriptionRecord objects to display
        """
        self._entries = entries

        # Clear existing widgets
        for widget in self._scrollable_frame.winfo_children():
            widget.destroy()

        # Create widgets for each entry
        for record in entries:
            self._create_entry_widget(self._scrollable_frame, record)

        # Update count label
        self._count_label.configure(text=f"{len(entries)} entries")

        # Reset scroll to top
        self._canvas.yview_moveto(0)

    def add_entry(self, record: TranscriptionRecord) -> None:
        """
        Add a new entry to the top of the list.

        Args:
            record: The TranscriptionRecord to add
        """
        self._entries.insert(0, record)

        # Create widget at the top
        entry_widget = self._create_entry_widget(self._scrollable_frame, record)

        # Move to top (pack at top)
        entry_widget.pack_forget()
        entry_widget.pack(fill=tk.X, pady=2, before=self._scrollable_frame.winfo_children()[1]
                         if len(self._scrollable_frame.winfo_children()) > 1 else None)

        # Update count
        self._count_label.configure(text=f"{len(self._entries)} entries")

    def toggle(self) -> None:
        """Toggle panel visibility."""
        if self._visible:
            self.hide()
        else:
            self.show()

    def show(self) -> None:
        """Show the history panel."""
        self._visible = True
        self._window.deiconify()
        self._window.lift()

    def hide(self) -> None:
        """Hide the history panel."""
        self._visible = False
        self._window.withdraw()

    @property
    def visible(self) -> bool:
        """Whether the panel is currently visible."""
        return self._visible

    def destroy(self) -> None:
        """Destroy the panel window."""
        try:
            self._canvas.unbind_all("<MouseWheel>")
            self._window.destroy()
        except tk.TclError:
            pass
