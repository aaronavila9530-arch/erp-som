const base = require("./app.json");

const kioskUser = process.env.EXPO_PUBLIC_ERP_SOM_KIOSK_USER || "";

const kioskProfiles = {
  "erasmo.gomez": {
    name: "ERP SOM Erasmo",
    scheme: "erpsom-erasmo",
    package: "com.msltech.erpsom",
    versionCode: 17281
  },
  "patricia.omier": {
    name: "ERP SOM Patricia",
    scheme: "erpsom-patricia",
    package: "com.msltech.erpsom",
    versionCode: 17282
  }
};

module.exports = ({ config }) => {
  const expo = { ...base.expo, ...config };
  const profile = kioskProfiles[kioskUser];

  if (!profile) return expo;

  return {
    ...expo,
    name: profile.name,
    scheme: profile.scheme,
    updates: {
      enabled: false
    },
    android: {
      ...expo.android,
      package: profile.package,
      versionCode: profile.versionCode
    },
    extra: {
      ...expo.extra,
      kioskUser
    }
  };
};
