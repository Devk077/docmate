/**
 * DoqToq Frontend Logger
 * Structured console logging with levels, timestamps, and module tags.
 * Enabled in dev mode (VITE_LOG_LEVEL env var or always in dev build).
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

const LEVEL_RANK: Record<LogLevel, number> = { debug: 0, info: 1, warn: 2, error: 3 };

const MIN_LEVEL: LogLevel =
  (import.meta.env.VITE_LOG_LEVEL as LogLevel) ||
  (import.meta.env.DEV ? 'debug' : 'warn');

const STYLES: Record<LogLevel, string> = {
  debug: 'color:#8892b0;font-weight:normal',
  info:  'color:#6c63ff;font-weight:600',
  warn:  'color:#ffd93d;font-weight:600',
  error: 'color:#ff5370;font-weight:700',
};

function ts(): string {
  return new Date().toISOString().slice(11, 23); // HH:MM:SS.mmm
}

function log(level: LogLevel, module: string, message: string, ...args: unknown[]) {
  if (LEVEL_RANK[level] < LEVEL_RANK[MIN_LEVEL]) return;

  const prefix = `%c[${ts()}] [${level.toUpperCase().padEnd(5)}] [${module}]`;
  const style  = STYLES[level];

  switch (level) {
    case 'debug': console.debug(prefix, style, message, ...args); break;
    case 'info':  console.info (prefix, style, message, ...args); break;
    case 'warn':  console.warn (prefix, style, message, ...args); break;
    case 'error': console.error(prefix, style, message, ...args); break;
  }
}

export function createLogger(module: string) {
  return {
    debug: (msg: string, ...args: unknown[]) => log('debug', module, msg, ...args),
    info:  (msg: string, ...args: unknown[]) => log('info',  module, msg, ...args),
    warn:  (msg: string, ...args: unknown[]) => log('warn',  module, msg, ...args),
    error: (msg: string, ...args: unknown[]) => log('error', module, msg, ...args),
  };
}
