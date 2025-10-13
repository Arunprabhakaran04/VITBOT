import Cookies from "js-cookie";
import { PersistStorage } from "zustand/middleware";

export const cookieStorage: PersistStorage<unknown> = {
  getItem: (name: string) => {
    const value = Cookies.get(name);
    return value ? JSON.parse(value) : null;
  },
  setItem: (name: string, value: unknown) => {
    Cookies.set(name, JSON.stringify(value), {
      expires: 7, // 7 days
      secure: process.env.NODE_ENV === "production",
      sameSite: "strict",
    });
  },
  removeItem: (name: string) => {
    Cookies.remove(name);
  },
};

// Helper function to clear all app-related cookies
export const clearAllAppCookies = () => {
  // Clear the main storage cookie
  Cookies.remove("rag-chatbot-storage");

  // Clear any other app-related cookies if they exist
  const allCookies = Cookies.get();
  Object.keys(allCookies).forEach((cookieName) => {
    if (
      cookieName.startsWith("rag-chatbot") ||
      cookieName.startsWith("vitbot")
    ) {
      Cookies.remove(cookieName);
    }
  });
};
