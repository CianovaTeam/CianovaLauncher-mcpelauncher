from PySide6.QtCore import QSize, QRect, QPoint, Qt
from PySide6.QtWidgets import QLayout, QWidgetItem, QLabel
from PySide6.QtGui import QPixmap, QPainter


def clear_layout(layout):
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.setParent(None)
            widget.deleteLater()
        else:
            sub_layout = item.layout()
            if sub_layout:
                clear_layout(sub_layout)


class FlowLayout(QLayout):
    """Layout that wraps its items onto new lines when the widget narrows,
    keeping header pills/indicators responsive to horizontal resizes.

    A single horizontal-expanding spacer (added via ``addSpacing(0)`` or a
    QSpacerItem) splits each line: items before it are left-aligned and items
    after it are right-aligned, matching a typical header (status on the left,
    selectors pushed to the right).
    """

    def __init__(self, parent=None, margin=0, h_spacing=8, v_spacing=6):
        super().__init__(parent)
        self._items = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def addSpacing(self, size):
        from PySide6.QtWidgets import QSpacerItem, QSizePolicy
        self.addItem(QSpacerItem(size, 0,
                                 QSizePolicy.Expanding,
                                 QSizePolicy.Minimum))

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _is_spacer(self, item):
        return item.spacerItem() is not None

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())

        # 1. Group items into lines based on wrapping width.
        lines = []
        current = []
        x = effective.x()
        for item in self._items:
            if self._is_spacer(item):
                current.append(item)
                continue
            item_w = item.sizeHint().width()
            if current and (x + item_w > effective.right() + 1):
                lines.append(current)
                current = []
                x = effective.x()
            current.append(item)
            x += item_w + self._h_spacing
        if current:
            lines.append(current)

        # 2. Position each line. A spacer splits left (start) / right (end).
        y = effective.y()
        for line in lines:
            spacer_idx = None
            for i, it in enumerate(line):
                if self._is_spacer(it):
                    spacer_idx = i
                    break
            items = [it for it in line if not self._is_spacer(it)]
            line_h = max((it.sizeHint().height() for it in items), default=0)

            if spacer_idx is None:
                cx = effective.x()
                for it in items:
                    if not test_only:
                        it.setGeometry(QRect(QPoint(cx, y), it.sizeHint()))
                    cx += it.sizeHint().width() + self._h_spacing
            else:
                left = items[:spacer_idx]
                right = items[spacer_idx:]
                left_w = sum(it.sizeHint().width() for it in left)
                left_w += self._h_spacing * max(0, len(left) - 1)
                right_w = sum(it.sizeHint().width() for it in right)
                right_w += self._h_spacing * max(0, len(right) - 1)

                cx = effective.x()
                for it in left:
                    if not test_only:
                        it.setGeometry(QRect(QPoint(cx, y), it.sizeHint()))
                    cx += it.sizeHint().width() + self._h_spacing

                rx = effective.right() - right_w
                if rx < cx:
                    rx = cx
                for it in right:
                    if not test_only:
                        it.setGeometry(QRect(QPoint(rx, y), it.sizeHint()))
                    rx += it.sizeHint().width() + self._h_spacing

            y += line_h + self._v_spacing

        return y - self._v_spacing - effective.y() + m.bottom()


class ResponsiveGridLayout(QLayout):
    """
    Responsive grid layout that arranges cards into columns with uniform width.
    Columns automatically expand equally to fill 100% of the available container width,
    preventing empty blank spaces on the right and ensuring the cards stay flush
    with surrounding UI toolbars.
    """

    def __init__(self, parent=None, margin=0, h_spacing=12, v_spacing=12, min_item_width=250, item_height=168, max_columns=None):
        super().__init__(parent)
        self._items = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._min_item_width = min_item_width
        self._item_height = item_height
        self._max_columns = max_columns
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        m = self.contentsMargins()
        w = self._min_item_width + m.left() + m.right()
        h = self._item_height + m.top() + m.bottom()
        return QSize(w, h)

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        effective_w = rect.width() - m.left() - m.right()
        if effective_w <= 0:
            effective_w = self._min_item_width

        items = [it for it in self._items if it.widget() is None or not it.widget().isHidden()]
        n_items = len(items)
        if n_items == 0:
            return m.top() + m.bottom()

        cols = max(1, (effective_w + self._h_spacing) // (self._min_item_width + self._h_spacing))
        if self._max_columns is not None:
            cols = min(self._max_columns, cols)
        total_spacing = (cols - 1) * self._h_spacing
        base_w = max(self._min_item_width, (effective_w - total_spacing) // cols)
        extra = (effective_w - total_spacing) % cols

        col_widths = [base_w + (1 if c < extra else 0) for c in range(cols)]
        col_x = []
        cur_x = rect.x() + m.left()
        for w in col_widths:
            col_x.append(cur_x)
            cur_x += w + self._h_spacing

        y = rect.y() + m.top()
        for i, item in enumerate(items):
            r = i // cols
            c = i % cols
            x = col_x[c]
            item_y = y + r * (self._item_height + self._v_spacing)
            w = col_widths[c]
            if not test_only:
                item.setGeometry(QRect(x, item_y, w, self._item_height))

        total_rows = (n_items + cols - 1) // cols
        total_h = total_rows * self._item_height + max(0, total_rows - 1) * self._v_spacing + m.top() + m.bottom()
        return total_h


class CreeperWatermarkWidget(QLabel):
    """
    Subtle faded Creeper watermark widget matching the launcher's opacity system.
    Transparent to mouse events and automatically positioned in the bottom-right corner.
    """
    def __init__(self, parent=None, target_height=195, opacity=0.38, margin_right=75, margin_bottom=35):
        super().__init__(parent)
        self.target_height = target_height
        self.opacity = opacity
        self.margin_right = margin_right
        self.margin_bottom = margin_bottom
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent; border: none;")
        self._init_pixmap()

    def _init_pixmap(self):
        import os
        from src.utils.resource_path import resource_path

        path = resource_path("creeper_forward.png")
        if not os.path.exists(path):
            path = resource_path("assets/media/creeper_forward.png")
        if not os.path.exists(path):
            return

        orig = QPixmap(path)
        if orig.isNull():
            return

        # Crop transparent margins around the creeper (bbox: 168, 4, 328, 446)
        cropped = orig.copy(168, 4, 328, 446)
        scaled = cropped.scaledToHeight(self.target_height, Qt.SmoothTransformation)
        faded = QPixmap(scaled.size())
        faded.fill(Qt.transparent)

        p = QPainter(faded)
        p.setOpacity(self.opacity)
        p.drawPixmap(0, 0, scaled)
        p.end()

        self.setPixmap(faded)
        self.setFixedSize(faded.size())

    def update_position(self):
        parent = self.parentWidget()
        if not parent or not self.pixmap() or self.pixmap().isNull():
            return
        pw = parent.width()
        ph = parent.height()
        x = max(0, pw - self.width() - self.margin_right)
        y = max(0, ph - self.height() - self.margin_bottom)
        self.move(x, y)
        self.lower()

