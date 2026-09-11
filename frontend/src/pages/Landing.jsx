import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";

export default function Landing() {
  return (
    <div className="page landing-page">
      <Navbar />
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
