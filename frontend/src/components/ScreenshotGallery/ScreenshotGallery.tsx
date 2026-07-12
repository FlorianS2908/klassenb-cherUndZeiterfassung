export function ScreenshotGallery({ items }: { items: { name: string; path: string }[] }) {
  return (
    <div className="gallery">
      {items.map((item) => (
        <article className="panel" key={item.name}>
          <strong>{item.name}</strong>
          <small>{item.path}</small>
        </article>
      ))}
    </div>
  );
}
