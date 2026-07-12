import { useEffect, useState } from 'react';
import { ScreenshotGallery } from '../components/ScreenshotGallery/ScreenshotGallery';
import { getScreenshots } from '../services/screenshotService';

export function ScreenshotsPage() {
  const [items, setItems] = useState<{ name: string; path: string }[]>([]);
  useEffect(() => {
    getScreenshots().then((result) => setItems(result.items));
  }, []);
  return <><div className="page-head"><h1>Screenshots</h1></div><ScreenshotGallery items={items} /></>;
}
