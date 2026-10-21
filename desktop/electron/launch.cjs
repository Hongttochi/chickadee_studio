// Launch the development app with its own macOS bundle name.
// Keep Electron's original installation untouched.
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync, spawn } = require("node:child_process");

const desktop = path.resolve(__dirname, "..");
let executable = require("electron");
if (process.platform === "darwin") {
  const version = require("electron/package.json").version;
  const directory = path.resolve(desktop, "../artifacts/dev-app", `${version}-branded-v2`);
  const bundle = path.join(directory, "Chickadee.app");
  const marker = path.join(directory, "ready-v2");
  if (!fs.existsSync(marker)) {
    fs.mkdirSync(directory, { recursive: true });
    const original = path.resolve(executable, "../../..");
    execFileSync("/usr/bin/ditto", [original, bundle]);
    const iconset = path.join(directory, "Chickadee.iconset");
    fs.mkdirSync(iconset, { recursive: true });
    for (const size of [16, 32, 128, 256, 512]) {
      for (const scale of [1, 2]) {
        const pixels = String(size * scale);
        const filename = `icon_${size}x${size}${scale === 2 ? "@2x" : ""}.png`;
        execFileSync("/usr/bin/sips", ["-z", pixels, pixels, path.join(desktop, "assets/app-mark.png"), "--out", path.join(iconset, filename)], { stdio: "ignore" });
      }
    }
    execFileSync("/usr/bin/iconutil", ["-c", "icns", iconset, "-o", path.join(bundle, "Contents/Resources/Chickadee.icns")]);
    const plist = path.join(bundle, "Contents/Info.plist");
    for (const [key, value] of Object.entries({
      CFBundleName: "Chickadee",
      CFBundleDisplayName: "Chickadee",
      CFBundleIdentifier: "org.chickadee.inspector.dev",
      CFBundleIconFile: "Chickadee.icns",
    })) {
      execFileSync("/usr/bin/plutil", ["-replace", key, "-string", value, plist]);
    }
    execFileSync("/usr/bin/codesign", ["--force", "--deep", "--sign", "-", bundle], { stdio: "inherit" });
    fs.writeFileSync(marker, version);
  }
  executable = path.join(bundle, "Contents/MacOS/Electron");
}

if (!process.argv.includes("--prepare")) {
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  const child = spawn(executable, [desktop], { env, stdio: "inherit" });
  child.on("error", error => { console.error(error); process.exitCode = 1; });
  child.on("exit", code => { process.exitCode = code ?? 0; });
}
