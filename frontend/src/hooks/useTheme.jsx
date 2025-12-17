import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const THEME_STORAGE_KEY = 'homelab-theme';
const ThemeContext = createContext({
  theme: 'system',
  resolvedTheme: 'light',
  setTheme: () => {},
});

const getSystemTheme = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'system';
    return localStorage.getItem(THEME_STORAGE_KEY) || 'system';
  });

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');

    const applyTheme = (value) => {
      const resolved = value === 'system' ? getSystemTheme() : value;
      const isDark = resolved === 'dark';
      document.documentElement.classList.toggle('dark', isDark);
      document.documentElement.setAttribute('data-theme', resolved);
    };

    applyTheme(theme);
    localStorage.setItem(THEME_STORAGE_KEY, theme);

    const handleChange = () => {
      if (theme === 'system') {
        applyTheme('system');
      }
    };

    media.addEventListener('change', handleChange);
    return () => media.removeEventListener('change', handleChange);
  }, [theme]);

  const value = useMemo(
    () => ({
      theme,
      resolvedTheme: theme === 'system' ? getSystemTheme() : theme,
      setTheme,
    }),
    [theme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}

