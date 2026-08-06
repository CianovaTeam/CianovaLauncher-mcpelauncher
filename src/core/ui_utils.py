from PySide6.QtCore import QSize, QRect, QPoint, Qt
from PySide6.QtWidgets import QLayout, QWidgetItem


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
            hint = item.sizeHint()
            next_x = x + hint.width() + self._h_spacing
            if (next_x - self._h_spacing > effective.right() + 1
                    and current):
                lines.append(current)
                current = []
                x = effective.x()
            current.append(item)
            x = next_x
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
