import { createContext, useContext } from "react";
import type { FeatureConfig } from "../api/types";

/** Optional server features (from /auth/config). Defaults to "off" when rendered without a provider. */
export const FeaturesContext = createContext<FeatureConfig>({ google: false, sandbox: false });

export const useFeatures = () => useContext(FeaturesContext);
