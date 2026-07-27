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
};

function normalizeOrder(order: unknown, itemIds: string[]): string[] {
  if (!Array.isArray(order)) return itemIds;
  const known = new Set(itemIds);
  const next = order.filter((id): id is string => typeof id === "string" && known.has(id));
  for (const id of itemIds) {
    if (!next.includes(id)) next.push(id);
  }
  return next;
}

function SortableGridCell({ item }: { item: SortableGridItem }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 20 : undefined,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`min-w-0 touch-none rounded-lg outline-none transition-shadow ${
        isDragging ? "cursor-grabbing opacity-90 shadow-lg ring-2 ring-teal-400" : "cursor-grab focus-visible:ring-2 focus-visible:ring-teal-500"
      } ${item.className ?? ""}`}
    >
      {item.node}
    </div>
  );
}

export function SortableGrid({
  storageKey,
  items,
  className,
  ariaLabel,
}: {
  storageKey: string;
  items: SortableGridItem[];
  className: string;
  ariaLabel: string;
}) {
  const itemIds = React.useMemo(() => items.map((item) => item.id), [items]);
  const [order, setOrder] = React.useState<string[]>(() => {
    try {
      return normalizeOrder(JSON.parse(window.localStorage.getItem(storageKey) ?? "null"), itemIds);
    } catch {
      return itemIds;
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
    window.localStorage.setItem(storageKey, JSON.stringify(order));
  }, [order, storageKey]);

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

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={orderedItems.map((item) => item.id)} strategy={rectSortingStrategy}>
        <section className={className} aria-label={ariaLabel}>
          {orderedItems.map((item) => (
            <SortableGridCell key={item.id} item={item} />
          ))}
        </section>
      </SortableContext>
    </DndContext>
  );
}
