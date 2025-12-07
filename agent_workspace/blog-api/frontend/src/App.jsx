import { useEffect, useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [posts, setPosts] = useState([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState("");

  const fetchPosts = async () => {
    try {
      const res = await axios.get(`${API_BASE}/posts/`);
      setPosts(res.data);
    } catch (err) {
      console.error(err);
      setError("Failed to fetch posts");
    }
  };

  useEffect(() => {
    fetchPosts();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    try {
      await axios.post(`${API_BASE}/posts/`, {
        title,
        content,
      });
      setTitle("");
      setContent("");
      fetchPosts();
    } catch (err) {
      console.error(err);
      setError(
        err?.response?.data?.detail || "Failed to create post"
      );
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: "2rem auto", fontFamily: "sans-serif" }}>
      <h1>Blog App</h1>

      <form onSubmit={handleSubmit} style={{ marginBottom: "2rem" }}>
        <input
          placeholder="Title"
          value={title}
          required
          onChange={(e) => setTitle(e.target.value)}
          style={{ width: "100%", padding: 8, marginBottom: 8 }}
        />
        <textarea
          placeholder="Content"
          value={content}
          required
          onChange={(e) => setContent(e.target.value)}
          rows={4}
          style={{ width: "100%", padding: 8, marginBottom: 8 }}
        />
        <button type="submit">Create Post</button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <h2>Posts</h2>
      {posts.length === 0 && <p>No posts yet.</p>}

      <ul>
        {posts.map((post) => (
          <li key={post.id} style={{ marginBottom: 12 }}>
            <strong>{post.title}</strong>
            <p>{post.content}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
