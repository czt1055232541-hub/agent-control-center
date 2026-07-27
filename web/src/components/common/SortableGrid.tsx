import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  rectSortingStrategy,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import React from "react";

export type SortableGridItem = {
  id: string;
  node: React.ReactNode;
  className?: string;
  defaultSize?: SortableGridItemSize;
};

type ResizeDirection = "horizontal" | "vertical" | "both";

type SortableGridItemSize = {
  colSpan: number;
  rowSpan: number;
};

const DEFAULT_ITEM_SIZE: SortableGridItemSize = { colSpan: 1, rowSpan: 1 };
const COLUMN_RESIZE_STEP_PX = 180;
const ROW_RESIZE_STEP_PX = 96;

function normalizeOrder(order: unknown, itemIds: string[]): string[] {
  if (!Array.isArray(order)) return itemIds;
  const known = new Set(itemIds);
  const next = order.filter((id): id is string => typeof id === "string" && known.has(id));
  for (const id of itemIds) {
    if (!next.includes(id)) next.push(id);
  }
  return next;
}

function normalizeSizes(sizes: unknown, items: SortableGridItem[], maxColSpan: number, maxRowSpan: number): Record<string, SortableGridItemSize> {
  const result: Record<string, SortableGridItemSize> = {};
  const source = sizes && typeof sizes === "object" ? sizes as Record<string, Partial<SortableGridItemSize>> : {};
  for (const item of items) {
    const fallback = item.defaultSize ?? DEFAULT_ITEM_SIZE;
    const current = source[item.id] ?? fallback;
    result[item.id] = {
      colSpan: clampSpan(current.colSpan, fallback.colSpan, maxColSpan),
      rowSpan: clampSpan(current.rowSpan, fallback.rowSpan, maxRowSpan),
    };
  }
  return result;
}

function clampSpan(value: unknown, fallback: number, max: number) {
  return Math.min(max, Math.max(1, Number.isFinite(value) ? Math.round(Number(value)) : fallback));
}

function SortableGridCell({
  item,
  size,
  onResize,
}: {
  item: SortableGridItem;
  size: SortableGridItemSize;
  onResize: (itemId: string, next: SortableGridItemSize) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 20 : undefined,
    "--sortable-col-span": size.colSpan,
    "--sortable-row-span": size.rowSpan,
  } as React.CSSProperties;

  const startResize = (event: React.PointerEvent<HTMLButtonElement>, direction: ResizeDirection) => {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.clientX;
    const startY = event.clientY;
    const startSize = { ...size };
    const pointerId = event.pointerId;
    event.currentTarget.setPointerCapture(pointerId);

    const move = (moveEvent: PointerEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const deltaY = moveEvent.clientY - startY;
      onResize(item.id, {
        colSpan: direction === "vertical" ? startSize.colSpan : Math.max(1, startSize.colSpan + Math.round(deltaX / COLUMN_RESIZE_STEP_PX)),
        rowSpan: direction === "horizontal" ? startSize.rowSpan : Math.max(1, startSize.rowSpan + Math.round(deltaY / ROW_RESIZE_STEP_PX)),
      });
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up, { once: true });
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`sortable-grid-cell relative min-w-0 touch-none rounded-lg outline-none transition-shadow ${
        isDragging ? "cursor-grabbing opacity-90 shadow-lg ring-2 ring-teal-400" : "cursor-grab focus-visible:ring-2 focus-visible:ring-teal-500"
      } ${item.className ?? ""}`}
    >
      {item.node}
      <button
        type="button"
        aria-label="Resize card width"
        className="absolute bottom-3 right-0 top-3 w-2 cursor-ew-resize rounded-full bg-teal-500/0 transition hover:bg-teal-500/30"
        onPointerDown={(event) => startResize(event, "horizontal")}
      />
      <button
        type="button"
        aria-label="Resize card height"
        className="absolute bottom-0 left-3 right-3 h-2 cursor-ns-resize rounded-full bg-teal-500/0 transition hover:bg-teal-500/30"
        onPointerDown={(event) => startResize(event, "vertical")}
      />
      <button
        type="button"
        aria-label="Resize card"
        className="absolute bottom-0 right-0 h-5 w-5 cursor-nwse-resize rounded-br-lg border-b-2 border-r-2 border-teal-500/50 bg-white/40"
        onPointerDown={(event) => startResize(event, "both")}
      />
    </div>
  );
}

export function SortableGrid({
  storageKey,
  items,
  className,
  ariaLabel,
  maxColSpan = 4,
  maxRowSpan = 4,
}: {
  storageKey: string;
  items: SortableGridItem[];
  className: string;
  ariaLabel: string;
  maxColSpan?: number;
  maxRowSpan?: number;
}) {
  const itemIds = React.useMemo(() => items.map((item) => item.id), [items]);
  const sizeStorageKey = `${storageKey}.sizes`;
  const [order, setOrder] = React.useState<string[]>(() => {
    try {
      return normalizeOrder(JSON.parse(window.localStorage.getItem(storageKey) ?? "null"), itemIds);
    } catch {
      return itemIds;
    }
  });
  const [sizes, setSizes] = React.useState<Record<string, SortableGridItemSize>>(() => {
    try {
      return normalizeSizes(JSON.parse(window.localStorage.getItem(sizeStorageKey) ?? "null"), items, maxColSpan, maxRowSpan);
    } catch {
      return normalizeSizes(null, items, maxColSpan, maxRowSpan);
    }
  });
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  React.useEffect(() => {
    setOrder((current) => normalizeOrder(current, itemIds));
  }, [itemIds]);

  React.useEffect(() => {
    setSizes((current) => normalizeSizes(current, items, maxColSpan, maxRowSpan));
  }, [items, maxColSpan, maxRowSpan]);

  React.useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(order));
  }, [order, storageKey]);

  React.useEffect(() => {
    window.localStorage.setItem(sizeStorageKey, JSON.stringify(sizes));
  }, [sizeStorageKey, sizes]);

  const orderedItems = React.useMemo(() => {
    const itemById = new Map(items.map((item) => [item.id, item]));
    return normalizeOrder(order, itemIds)
      .map((id) => itemById.get(id))
      .filter((item): item is SortableGridItem => Boolean(item));
  }, [itemIds, items, order]);

  const handleDragEnd = React.useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setOrder((current) => {
      const normalized = normalizeOrder(current, itemIds);
      const oldIndex = normalized.indexOf(String(active.id));
      const newIndex = normalized.indexOf(String(over.id));
      if (oldIndex === -1 || newIndex === -1) return normalized;
      return arrayMove(normalized, oldIndex, newIndex);
    });
  }, [itemIds]);
  const resizeItem = React.useCallback((itemId: string, next: SortableGridItemSize) => {
    setSizes((current) => {
      const fallback = current[itemId] ?? DEFAULT_ITEM_SIZE;
      return {
        ...current,
        [itemId]: {
          colSpan: clampSpan(next.colSpan, fallback.colSpan, maxColSpan),
          rowSpan: clampSpan(next.rowSpan, fallback.rowSpan, maxRowSpan),
        },
      };
    });
  }, [maxColSpan, maxRowSpan]);

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={orderedItems.map((item) => item.id)} strategy={rectSortingStrategy}>
        <section className={`sortable-grid ${className}`} aria-label={ariaLabel}>
          {orderedItems.map((item) => (
            <SortableGridCell key={item.id} item={item} size={sizes[item.id] ?? DEFAULT_ITEM_SIZE} onResize={resizeItem} />
          ))}
        </section>
      </SortableContext>
    </DndContext>
  );
}
