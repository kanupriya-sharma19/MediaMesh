import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";

const ROW_COUNT = 4;

function mixMedia(media) {
  const items = [...(media.movies || []), ...(media.music || []), ...(media.books || [])];
  return items.sort(() => Math.random() - 0.5);
}

export default function Landing() {
  const [media, setMedia] = useState([]);

  useEffect(() => {
    let active = true;
    api.landingMedia().then((result) => {
      if (active) setMedia(mixMedia(result));
    }).catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const rows = Array.from({ length: ROW_COUNT }, (_, index) => {
    const offset = index % Math.max(media.length, 1);
    return media.length ? [...media.slice(offset), ...media.slice(0, offset)] : [];
  });

  return (
    <div className="page landing-page">
      <div className="landing-media" aria-hidden="true">
        {rows.map((row, rowIndex) => (
          <div className={`media-marquee media-marquee-${rowIndex + 1}`} key={rowIndex}>
            <div className="media-track">
              {[...row, ...row].map((item, itemIndex) => (
                <img
                  key={`${item.type}-${item.title}-${itemIndex}`}
                  src={item.image_url}
                  alt=""
                  loading="lazy"
                  onError={(event) => {
                    event.currentTarget.style.visibility = "hidden";
                  }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      <main className="landing-main">
        <div className="kicker">Your media, connected</div>
        <h1>
          <span>Discover what links</span>
          <br />
          the things you love.
        </h1>
        <p>
          Ask one question across music, movies and books. MediaMesh finds the
          signal between them.
        </p>
        <div className="landing-actions">
          <Link className="primary-button" to="/login">
            Login <span>↗</span>
          </Link>
          <Link className="outline-button" to="/signup">
            Create an account
          </Link>
        </div>
        <div className="landing-foot">
          <span>MusicBrainz</span>
          <span>TMDB</span>
          <span>Google Books</span>
          <span>One connected conversation</span>
        </div>
      </main>
    </div>
  );
}
