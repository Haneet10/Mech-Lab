// worker.js — runs Python off the main thread so the UI never stutters.
//
// Boot: load Pyodide, copy the mech_toolkit sources listed in
// py/manifest.json into its virtual filesystem, import bridge.py.
// Then each message {id, name, args} becomes bridge.call(name, json).

const here = new URL(self.location.href);
const PYODIDE = here.searchParams.get("pyodide") || "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
const base = new URL("../py/", here);

const post = (msg) => self.postMessage(msg);
const stage = (text) => post({ type: "stage", text });

let call = null;

const ready = (async () => {
  stage("Downloading Python");
  const manifestP = fetch(new URL("manifest.json", base)).then((r) => r.json());
  importScripts(PYODIDE + "pyodide.js");
  const py = await self.loadPyodide({ indexURL: PYODIDE });

  stage("Loading mech_toolkit");
  const manifest = await manifestP;
  const files = await Promise.all(
    manifest.files.map(async (f) => [f, await (await fetch(new URL(f, base))).text()])
  );
  for (const [f, src] of files) {
    const dir = "/app/" + f.split("/").slice(0, -1).join("/");
    py.FS.mkdirTree(dir);
    py.FS.writeFile("/app/" + f, src);
  }
  py.runPython("import sys; sys.path.insert(0, '/app'); import bridge");
  call = py.globals.get("bridge").call;
  const version = py.runPython("import sys; '.'.join(map(str, sys.version_info[:3]))");
  return { python: version, toolkit: manifest.version, commit: manifest.commit, tests: manifest.tests };
})();

ready.then(
  (info) => post({ type: "ready", info }),
  (err) => post({ type: "fatal", error: String(err && err.message ? err.message : err) })
);

self.onmessage = async (e) => {
  const { id, name, args } = e.data;
  try {
    await ready;
    const t0 = performance.now();
    const out = JSON.parse(call(name, JSON.stringify(args ?? {})));
    post({ ...out, type: "result", id, ms: performance.now() - t0 });
  } catch (err) {
    post({ type: "result", id, ok: false, error: String(err && err.message ? err.message : err) });
  }
};
