    import dotenv from 'dotenv';
dotenv.config();

export const CONFIG = {
  BOT_TOKEN: process.env.BOT_TOKEN || '',
  SUPABASE_URL: (process.env.SUPABASE_URL || '').replace(/\/$/, ''),
  SUPABASE_KEY: process.env.SUPABASE_KEY || '',
  FUSION_TOPIC_ID: Number(process.env.FUSION_TOPIC_ID) || 0,
  TRIVIA_TOPIC_ID: Number(process.env.TRIVIA_TOPIC_ID) || 0,
  LEADERBOARDS_TOPIC_ID: Number(process.env.LEADERBOARDS_TOPIC_ID) || 0,
  CHECKMATE_HQ_GROUP_ID: Number(process.env.CHECKMATE_HQ_GROUP_ID) || 0
};

export const STICKERS = {
  ACCESS_DENIED: "CAACAgQAAxkBAAFIQ_lp8GsJepZi0KF6r2mfAl_WppJJmAAC-xkAAvSegFORr5sV0ZQ50TsE",
  NEW_ROUND: "CAACAgQAAxkBAAFIQ_Vp8GsBLJUMxVfnCZf1T2USv9LcmQACTS0AAhhCgVMpo0o9nkUv1TsE",
  UNREGISTERED: "CAACAgQAAxkBAAFIQ_dp8GsGpaBG4Mwq8eLR2KssKRZNigACYB8AAkTagVMHGNklL-OePzsE",
  CRATE_DROP: "CAACAgQAAxkBAAFIQ9hp8Go_f_MiW-ZSQUiR8aGCuPhZzwAC6B0AAnpiiVMDM_gbbCe70TsE"
};

export const DIVIDER = "━━━━━━━━━━━━━━━━━━━━━";