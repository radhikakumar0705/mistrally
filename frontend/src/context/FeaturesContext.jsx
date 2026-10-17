import { createContext, useContext } from "react";

/** Optional server features (from /auth/config). Defaults to "off" when rendered without a provider. */
export const FeaturesContext = createContext({ google: false, sandbox: false });

export const useFeatures = () => useContext(FeaturesContext);
