import { getApps, initializeApp } from "firebase/app";
import { getAuth, onAuthStateChanged, type Auth, type User } from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID
};

let authInstance: Auth | null = null;

export function getFirebaseAuth(): Auth {
  if (!firebaseConfig.apiKey || !firebaseConfig.projectId) throw new Error("Firebase public configuration is missing.");
  if (authInstance) return authInstance;
  const firebaseApp = getApps()[0] ?? initializeApp(firebaseConfig);
  authInstance = getAuth(firebaseApp);
  return authInstance;
}

export async function getAuthenticatedUser(): Promise<User | null> {
  const auth = getFirebaseAuth();
  if (auth.currentUser) return auth.currentUser;
  return new Promise((resolve) => {
    const unsubscribe = onAuthStateChanged(auth, (user) => { unsubscribe(); resolve(user); });
  });
}
