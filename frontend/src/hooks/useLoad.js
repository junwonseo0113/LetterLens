import { useEffect, useState } from "react";

// Loads data for a screen section and keeps "loading", "loaded" and
// "failed" distinct -- a failed request must never look like an empty
// result (e.g. "No upcoming deadlines" when deadlines didn't load).
// `deps` work like useEffect's; `reload()` retries. While reloading the
// same thing, the previous data stays on screen (so a re-check after
// answering a question doesn't wipe what's being typed elsewhere).
export function useLoad(load, deps) {
  const [attempt, setAttempt] = useState(0);
  const baseKey = JSON.stringify(deps);
  const key = JSON.stringify([baseKey, attempt]);
  const [state, setState] = useState({ key: null, baseKey: null, data: undefined, error: null });

  useEffect(() => {
    let cancelled = false;
    load()
      .then((data) => !cancelled && setState({ key, baseKey, data, error: null }))
      .catch((error) => !cancelled && setState({ key, baseKey, data: undefined, error }));
    return () => {
      cancelled = true;
    };
    // `load` is a fresh closure each render; `key` captures what it depends on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const current = state.key === key;
  const sameThing = state.baseKey === baseKey;
  return {
    loading: !current && !(sameThing && state.data !== undefined),
    refreshing: !current,
    data: current || sameThing ? state.data : undefined,
    error: current ? state.error : null,
    reload: () => setAttempt((n) => n + 1),
  };
}
