import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import { useLanguage } from "../context/useLanguage";
import { uploadLetter } from "../api";

// Shared by every camera button: uploads a letter photo, keeps the photo so
// a failed upload can be retried, and exposes the error to show.
export function useLetterUpload({ replace = false } = {}) {
  const { language } = useLanguage();
  const { token } = useAuth();
  const navigate = useNavigate();
  const lastFileRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  async function upload(file) {
    lastFileRef.current = file;
    setUploading(true);
    setError(null);
    try {
      const result = await uploadLetter({ file, language: language || "en", token });
      lastFileRef.current = null;
      navigate(`/letters/${result.letter_id}`, { state: { result }, replace });
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  }

  function onFileChange(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) upload(file);
  }

  return {
    uploading,
    error,
    onFileChange,
    retry: () => lastFileRef.current && upload(lastFileRef.current),
    dismiss: () => setError(null),
  };
}
