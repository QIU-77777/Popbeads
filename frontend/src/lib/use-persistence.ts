/**
 * use-persistence.ts
 *
 * 提供两套持久化工具，用于在页面刷新后恢复状态：
 *
 * 1. localStorage  — 保存轻量级纯文本参数（生成参数、AI Prompt、Switch 状态等）
 * 2. IndexedDB     — 保存图片 base64（上传原图、AI 编辑结果图）
 *
 * 对外暴露:
 *   useLocalStorage<T>(key, defaultValue)   — 类似 useState，自动读写 localStorage
 *   useSessionId()                          — 返回当前浏览器唯一 session ID（UUID，持久化）
 *   saveImageToIDB(key, dataUrl)            — 存储图片 data URL 到 IndexedDB
 *   loadImageFromIDB(key)                   — 读取图片 data URL（不存在返回 null）
 *   removeImageFromIDB(key)                 — 删除指定 key 的图片
 *   clearAllImagesFromIDB()                 — 清空所有图片缓存（换图时调用）
 *
 * IndexedDB 结构:
 *   DB: "pingdou_cache"  版本: 1
 *   Store: "images"  keyPath: "key"
 *   Record: { key: string, dataUrl: string, savedAt: number }
 */

"use client";

import { useState, useEffect, useCallback } from "react";

// ── IndexedDB 常量 ──
const IDB_NAME = "pingdou_cache";
const IDB_VERSION = 1;
const IDB_STORE = "images";

/** 打开（或创建）IndexedDB 数据库，返回 IDBDatabase 实例。 */
function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, IDB_VERSION);

    req.onupgradeneeded = (e) => {
      const db = (e.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(IDB_STORE)) {
        db.createObjectStore(IDB_STORE, { keyPath: "key" });
      }
    };

    req.onsuccess = (e) => resolve((e.target as IDBOpenDBRequest).result);
    req.onerror = () => reject(req.error);
  });
}

/** 保存图片 data URL 到 IndexedDB。 */
export async function saveImageToIDB(key: string, dataUrl: string): Promise<void> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(IDB_STORE, "readwrite");
      tx.objectStore(IDB_STORE).put({ key, dataUrl, savedAt: Date.now() });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch (e) {
    console.warn("[persistence] saveImageToIDB failed:", e);
  }
}

/** 从 IndexedDB 读取图片 data URL，不存在返回 null。 */
export async function loadImageFromIDB(key: string): Promise<string | null> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(IDB_STORE, "readonly");
      const req = tx.objectStore(IDB_STORE).get(key);
      req.onsuccess = () => resolve((req.result as { dataUrl: string } | undefined)?.dataUrl ?? null);
      req.onerror = () => reject(req.error);
    });
  } catch (e) {
    console.warn("[persistence] loadImageFromIDB failed:", e);
    return null;
  }
}

/** 从 IndexedDB 删除指定 key 的图片记录。 */
export async function removeImageFromIDB(key: string): Promise<void> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(IDB_STORE, "readwrite");
      tx.objectStore(IDB_STORE).delete(key);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch (e) {
    console.warn("[persistence] removeImageFromIDB failed:", e);
  }
}

/** 清空 IndexedDB 中所有图片缓存（用户重新上传图片时调用）。 */
export async function clearAllImagesFromIDB(): Promise<void> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(IDB_STORE, "readwrite");
      tx.objectStore(IDB_STORE).clear();
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch (e) {
    console.warn("[persistence] clearAllImagesFromIDB failed:", e);
  }
}

/**
 * useLocalStorage — 与 React useState 同签名，自动同步到 localStorage。
 *
 * - SSR 安全：服务器端返回 defaultValue，客户端挂载后读取实际存储值
 * - 序列化：JSON.stringify / JSON.parse
 * - 失败时静默降级为内存 state，不抛错
 *
 * @param key          localStorage 键名（建议加前缀如 "pingdou_"）
 * @param defaultValue 默认值，首次访问或解析失败时使用
 */
/**
 * useSessionId — 返回当前浏览器的唯一 session ID。
 *
 * - 首次访问时生成一个 UUID v4 并写入 localStorage（key: "pingdou_session_id"）
 * - 后续刷新/重开标签页时读取同一个值
 * - 不同用户的浏览器各自生成独立 ID，用于在后端区分来源
 */
export function useSessionId(): string {
  const SESSION_KEY = "pingdou_session_id";
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    try {
      let id = localStorage.getItem(SESSION_KEY);
      if (!id) {
        // 生成 UUID v4（crypto.randomUUID 在现代浏览器中广泛支持）
        id = typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        localStorage.setItem(SESSION_KEY, id);
      }
      setSessionId(id);
    } catch (e) {
      console.warn("[persistence] useSessionId failed:", e);
    }
  }, []);

  return sessionId;
}

export function useLocalStorage<T>(key: string, defaultValue: T): [T, (value: T | ((prev: T) => T)) => void] {
  // 初始值使用 defaultValue（保证 SSR 一致），客户端 mount 后再同步
  const [storedValue, setStoredValue] = useState<T>(defaultValue);

  // 客户端挂载后，读取 localStorage 中已存储的值
  useEffect(() => {
    try {
      const item = localStorage.getItem(key);
      if (item !== null) {
        setStoredValue(JSON.parse(item) as T);
      }
    } catch (e) {
      console.warn("[persistence] localStorage read failed:", key, e);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const next = typeof value === "function" ? (value as (p: T) => T)(prev) : value;
        try {
          localStorage.setItem(key, JSON.stringify(next));
        } catch (e) {
          console.warn("[persistence] localStorage write failed:", key, e);
        }
        return next;
      });
    },
    [key]
  );

  return [storedValue, setValue];
}
