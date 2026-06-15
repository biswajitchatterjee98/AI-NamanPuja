import { useState } from "react";

type Props = {
  path: string;
  alt: string;
  caption: string;
  loading?: boolean;
};

export default function PageImage({ path, alt, caption, loading = false }: Props) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const showSpinner = loading || (!loaded && !failed);

  return (
    <figure className="page-image-card">
      <div className={`page-image-frame${showSpinner ? " is-loading" : ""}`}>
        {showSpinner && (
          <div className="page-image-loader" aria-label="Loading image">
            <span className="spinner" />
            <span>{loading ? "Generating image…" : "Loading image…"}</span>
          </div>
        )}
        {!loading && (
          <img
            src={path}
            alt={alt || caption}
            loading="lazy"
            onLoad={() => setLoaded(true)}
            onError={() => setFailed(true)}
            style={{ opacity: loaded ? 1 : 0 }}
          />
        )}
        {failed && !loading && (
          <p className="page-image-error">Image could not be loaded</p>
        )}
      </div>
      <figcaption>{caption || alt}</figcaption>
    </figure>
  );
}
