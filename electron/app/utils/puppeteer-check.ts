/**
 * puppeteer-check.ts
 *
 * Detects Chromium (or Chrome) for Puppeteer. We support Chromium from
 * browser-snapshots; the setup installer installs Chromium into the cache.
 */
import fs from "fs";
import os from "os";
import path from "path";
import puppeteer from "puppeteer";
import { Browser, getInstalledBrowsers } from "@puppeteer/browsers";

function getPuppeteerCacheDir(): string {
  const configCache =
    (puppeteer as any).configuration?.cacheDirectory ??
    (puppeteer as any).defaultDownloadPath;
  return configCache ?? path.join(os.homedir(), ".cache", "puppeteer");
}

function shouldSkipDownload(): boolean {
  if (process.env.PUPPETEER_SKIP_DOWNLOAD) {
    const value = process.env.PUPPETEER_SKIP_DOWNLOAD.trim().toLowerCase();
    return value === "1" || value === "true" || value === "yes";
  }
  return Boolean((puppeteer as any).configuration?.skipDownload);
}

/** Status for the unified setup installer (what’s missing). */
export interface SetupStatus {
  needsLibreOffice: boolean;
  needsChrome: boolean;
  needsImageMagick: boolean;
}

/**
 * Returns the path to the browser executable to use for Puppeteer: either
 * Chrome (Puppeteer default) if present, or Chromium from the cache.
 *
 * NOTE: Detection must NOT be gated by shouldSkipDownload(). That flag only
 * controls whether npm postinstall downloads a browser; it must never prevent
 * the app from finding an already-installed browser at runtime.
 */
export async function getPuppeteerExecutablePath(): Promise<string | undefined> {
  const chromePath = puppeteer.executablePath();
  if (chromePath && fs.existsSync(chromePath)) return chromePath;
  const cacheDir = getPuppeteerCacheDir();
  const browsers = await getInstalledBrowsers({ cacheDir });
  // Check for Chromium first, then fall back to Chrome for Testing
  const chromium = browsers.find((b) => b.browser === Browser.CHROMIUM);
  if (chromium?.executablePath && fs.existsSync(chromium.executablePath)) {
    return chromium.executablePath;
  }
  const chrome = browsers.find((b) => b.browser === Browser.CHROME);
  if (chrome?.executablePath && fs.existsSync(chrome.executablePath)) {
    return chrome.executablePath;
  }
  return undefined;
}

/**
 * Returns true if a supported browser (Chrome or Chromium) is already installed.
 */
export async function isChromeInstalled(): Promise<boolean> {
  const execPath = await getPuppeteerExecutablePath();
  return Boolean(execPath);
}

/**
 * Status for Puppeteer/Chromium (used by UI). Installation is done via the
 * unified setup window, not here.
 */
export type PuppeteerStatus =
  | "checking"
  | "installed"
  | "missing"
  | "downloading"
  | "downloaded"
  | "skipped"
  | "failed";

/**
 * Checks whether Chromium (or Chrome) is available. Does not install;
 * use the unified setup window to install.
 */
export async function checkPuppeteerChromiumBeforeWindow(
  onStatus?: (status: PuppeteerStatus) => void
): Promise<boolean> {
  onStatus?.("checking");
  if (shouldSkipDownload()) {
    console.log("[Puppeteer] Skip download enabled.");
    onStatus?.("skipped");
    return true;
  }
  const executablePath = await getPuppeteerExecutablePath();
  if (executablePath) {
    console.log(`[Puppeteer] Browser found at ${executablePath}`);
    onStatus?.("installed");
    return true;
  }
  onStatus?.("missing");
  return true;
}
