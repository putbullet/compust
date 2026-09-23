/**
 * Cross-browser Promise-based API wrapper supporting Chrome, Edge, Brave, and Firefox.
 * Uses window.browser or window.chrome with async wrappers.
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const globalScope = (typeof globalThis !== 'undefined' ? globalThis : self) as any;

export const isFirefox = typeof globalScope.browser !== 'undefined' && !!globalScope.browser.runtime;

export const browserAPI = {
  storage: {
    local: {
      async get<T = Record<string, any>>(keys?: string | string[] | Record<string, any>): Promise<T> {
        if (typeof globalScope.browser !== 'undefined' && globalScope.browser.storage?.local) {
          return globalScope.browser.storage.local.get(keys);
        }
        if (typeof globalScope.chrome !== 'undefined' && globalScope.chrome.storage?.local) {
          return new Promise((resolve, reject) => {
            globalScope.chrome.storage.local.get(keys, (result: any) => {
              if (globalScope.chrome.runtime.lastError) {
                reject(new Error(globalScope.chrome.runtime.lastError.message));
              } else {
                resolve(result as T);
              }
            });
          });
        }
        return {} as T;
      },
      async set(items: Record<string, any>): Promise<void> {
        if (typeof globalScope.browser !== 'undefined' && globalScope.browser.storage?.local) {
          return globalScope.browser.storage.local.set(items);
        }
        if (typeof globalScope.chrome !== 'undefined' && globalScope.chrome.storage?.local) {
          return new Promise((resolve, reject) => {
            globalScope.chrome.storage.local.set(items, () => {
              if (globalScope.chrome.runtime.lastError) {
                reject(new Error(globalScope.chrome.runtime.lastError.message));
              } else {
                resolve();
              }
            });
          });
        }
      },
      async remove(keys: string | string[]): Promise<void> {
        if (typeof globalScope.browser !== 'undefined' && globalScope.browser.storage?.local) {
          return globalScope.browser.storage.local.remove(keys);
        }
        if (typeof globalScope.chrome !== 'undefined' && globalScope.chrome.storage?.local) {
          return new Promise((resolve, reject) => {
            globalScope.chrome.storage.local.remove(keys, () => {
              if (globalScope.chrome.runtime.lastError) {
                reject(new Error(globalScope.chrome.runtime.lastError.message));
              } else {
                resolve();
              }
            });
          });
        }
      },
    },
  },
  runtime: {
    async sendMessage<T = any>(message: any): Promise<T> {
      if (typeof globalScope.browser !== 'undefined' && globalScope.browser.runtime?.sendMessage) {
        return globalScope.browser.runtime.sendMessage(message);
      }
      if (typeof globalScope.chrome !== 'undefined' && globalScope.chrome.runtime?.sendMessage) {
        return new Promise((resolve, reject) => {
          globalScope.chrome.runtime.sendMessage(message, (response: any) => {
            if (globalScope.chrome.runtime.lastError) {
              reject(new Error(globalScope.chrome.runtime.lastError.message));
            } else {
              resolve(response as T);
            }
          });
        });
      }
      throw new Error('Runtime messaging API not available');
    },
    onMessage: {
      addListener(callback: (message: any, sender: any, sendResponse: (res?: any) => void) => boolean | void) {
        if (typeof globalScope.browser !== 'undefined' && globalScope.browser.runtime?.onMessage) {
          globalScope.browser.runtime.onMessage.addListener(callback);
        } else if (typeof globalScope.chrome !== 'undefined' && globalScope.chrome.runtime?.onMessage) {
          globalScope.chrome.runtime.onMessage.addListener(callback);
        }
      },
    },
    getURL(path: string): string {
      if (typeof globalScope.browser !== 'undefined' && globalScope.browser.runtime?.getURL) {
        return globalScope.browser.runtime.getURL(path);
      }
      if (typeof globalScope.chrome !== 'undefined' && globalScope.chrome.runtime?.getURL) {
        return globalScope.chrome.runtime.getURL(path);
      }
      return path;
    },
    openOptionsPage(): Promise<void> {
      if (typeof globalScope.browser !== 'undefined' && globalScope.browser.runtime?.openOptionsPage) {
        return globalScope.browser.runtime.openOptionsPage();
      }
      if (typeof globalScope.chrome !== 'undefined' && globalScope.chrome.runtime?.openOptionsPage) {
        return new Promise((resolve) => {
          globalScope.chrome.runtime.openOptionsPage(() => resolve());
        });
      }
      return Promise.resolve();
    },
  },
  tabs: {
    async create(createProperties: { url: string }): Promise<void> {
      if (typeof globalScope.browser !== 'undefined' && globalScope.browser.tabs?.create) {
        await globalScope.browser.tabs.create(createProperties);
        return;
      }
      if (typeof globalScope.chrome !== 'undefined' && globalScope.chrome.tabs?.create) {
        return new Promise((resolve) => {
          globalScope.chrome.tabs.create(createProperties, () => resolve());
        });
      }
    },
  },
};
