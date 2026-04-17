import {
  COMMON_SUFFIXES,
  DEFAULT_ROUTERS,
  HARD_LIMIT,
  MAX_RANDOM_COUNT,
  MAX_TOTAL_NAMES,
  YEAR_END,
  YEAR_START
} from "./constants.js";
import {
  buildForms,
  clampNumber,
  sanitizeSize,
  unique
} from "./utils.js";

function buildRandomSuffixes(count) {
  const capped = clampNumber(count, 0, MAX_RANDOM_COUNT);
  const values = new Set();

  while (values.size < capped) {
    const candidate = Math.floor(Math.random() * 999999) + 1;
    values.add(String(candidate));
  }

  return [...values];
}

function dobVariants(dobToken) {
  const cleaned = String(dobToken || "").replace(/\D+/g, "");
  const variants = new Set();

  if (!cleaned) return [];
  variants.add(cleaned);

  if (cleaned.length === 8) {
    const dd = cleaned.slice(0, 2);
    const mm = cleaned.slice(2, 4);
    const yyyy = cleaned.slice(4, 8);
    variants.add(`${dd}${mm}${yyyy}`);
    variants.add(`${dd}${mm}${yyyy.slice(2)}`);
    variants.add(`${yyyy}${mm}${dd}`);
    variants.add(yyyy);
  } else if (cleaned.length === 6) {
    variants.add(cleaned.slice(0, 4));
    variants.add(cleaned.slice(2, 6));
  }

  return [...variants];
}

function addWithForms(set, base, includeLeet) {
  buildForms(base, includeLeet).forEach((item) => {
    set.add(item);
    set.add(`@${item}`);
    set.add(`#${item}`);
    set.add(`!${item}`);
  });
}

function addWithSuffixes(set, base, suffixes, includeLeet) {
  const forms = buildForms(base, includeLeet);
  forms.forEach((form) => {
    set.add(form);
    suffixes.forEach((suffix) => {
      set.add(`${form}${suffix}`);
      set.add(`${form}@${suffix}`);
      set.add(`${form}#${suffix}`);
      set.add(`${form}!${suffix}`);
      set.add(`${form}${suffix}${suffix}`);
    });
  });
}

function addYearCombos(set, base, includeLeet) {
  const forms = buildForms(base, includeLeet);
  forms.forEach((form) => {
    for (let year = YEAR_START; year <= YEAR_END; year += 1) {
      set.add(`${form}${year}`);
      set.add(`${form}@${year}`);
      set.add(`${form}#${year}`);
      set.add(`${form}!${year}`);
    }
  });
}

function addRouterDefaults(set, includeLeet) {
  DEFAULT_ROUTERS.forEach((router) => {
    addWithForms(set, router, includeLeet);
    set.add(router.replace("@", "#"));
    set.add(router.replace("@", "!"));
    set.add(router.replace("tp-link", "tplink"));
  });
}

function topUpCandidates(set, requestedSize, bases, includeLeet) {
  if (set.size >= requestedSize) return 0;

  const formPool = unique(
    bases.flatMap((base) => buildForms(base, includeLeet)).filter(Boolean)
  );

  if (!formPool.length) return 0;

  const pool = formPool;
  const before = set.size;
  const maxAttempts = Math.max(7000, requestedSize * 10);

  for (let attempts = 0; attempts < maxAttempts && set.size < requestedSize; attempts += 1) {
    const base = pool[attempts % pool.length];
    const friend = pool[(attempts * 3 + 7) % pool.length];
    const n2 = Math.floor(Math.random() * 90) + 10;
    const n4 = Math.floor(Math.random() * 9000) + 1000;
    const n6 = Math.floor(Math.random() * 900000) + 100000;
    const yy = Math.floor(Math.random() * 30) + 70;

    set.add(`${base}${n4}`);
    set.add(`${base}@${n4}`);
    set.add(`${base}#${n4}`);
    set.add(`${base}!${n4}`);
    set.add(`${n4}${base}`);

    set.add(`${base}${friend}${n2}`);
    set.add(`${base}@${friend}${n4}`);
    set.add(`${base}.${friend}${n2}`);
    set.add(`${base}_${friend}${n2}`);

    set.add(`${base.replace(/a/g, "@")}@${n2}`);
    set.add(`${base.replace(/i/g, "!")}${n2}${n2}`);
    set.add(`${base.replace(/o/g, "0")}${yy}`);
    set.add(`${friend.replace(/s/g, "$")}${n6}`);

    if (attempts % 2 === 0) {
      set.add(`${base}@${friend}@${n2}`);
      set.add(`${base}#${friend}#${n2}`);
      set.add(`${base}!${friend}!${n2}`);
    }
  }

  return set.size - before;
}

export function generateWordlist(input) {
  const warnings = [];
  const {
    owners,
    lastNames,
    family,
    pets,
    phoneNumbers,
    locations,
    interests,
    exactDob,
    includeRouterDefaults,
    includeYears,
    includeLeet,
    includeRandomNumbers,
    randomCount,
    desiredSize
  } = input;

  const names = unique([...owners, ...lastNames, ...family, ...pets]).slice(0, MAX_TOTAL_NAMES);
  if (names.length < owners.length + lastNames.length + family.length) {
    warnings.push(`Names were trimmed to first ${MAX_TOTAL_NAMES} entries for performance.`);
  }
  if (names.length === 0) {
    warnings.push("No name tokens provided; generation will use only supplied non-name fields.");
  }

  const baseNames = names;
  const baseLocations = locations;
  const baseInterests = interests;
  const dobList = unique(exactDob.flatMap((dob) => dobVariants(dob)));
  const phones = unique([...phoneNumbers]);
  const randomSuffixes = includeRandomNumbers ? buildRandomSuffixes(randomCount) : [];
  const suffixPool = includeRandomNumbers
    ? unique([...COMMON_SUFFIXES, ...randomSuffixes])
    : COMMON_SUFFIXES;

  const { requestedRaw, requestedSize } = sanitizeSize(desiredSize);
  if (requestedRaw < 100) {
    warnings.push("Requested size below minimum and was raised to 100.");
  }
  if (requestedRaw > HARD_LIMIT) {
    warnings.push(`Requested size exceeded hard limit and was capped at ${HARD_LIMIT}.`);
  }

  const candidates = new Set();

  // 1) Base patterns for names
  baseNames.forEach((name) => {
    addWithSuffixes(candidates, name, suffixPool, includeLeet);
    if (includeYears) {
      addYearCombos(candidates, name, includeLeet);
    }

    dobList.forEach((dob) => {
      addWithForms(candidates, `${name}${dob}`, includeLeet);
      addWithForms(candidates, `${name}@${dob}`, includeLeet);
      addWithForms(candidates, `${name}#${dob}`, includeLeet);
      addWithForms(candidates, `${name}!${dob}`, includeLeet);
    });
  });

  // 2) Name + location / interest patterns
  baseNames.forEach((name) => {
    baseLocations.forEach((loc) => {
      addWithForms(candidates, `${name}${loc}`, includeLeet);
      addWithForms(candidates, `${loc}${name}`, includeLeet);
      addWithForms(candidates, `${name}@${loc}`, includeLeet);
      addWithForms(candidates, `${loc}@${name}`, includeLeet);
      addWithSuffixes(candidates, `${name}${loc}`, ["123", "2024", "786"], includeLeet);
    });

    baseInterests.forEach((interest) => {
      addWithForms(candidates, `${name}${interest}`, includeLeet);
      addWithForms(candidates, `${name}@${interest}`, includeLeet);
      addWithSuffixes(candidates, `${name}${interest}`, ["123", "2024", "786"], includeLeet);
    });
  });

  // 3) Pair combinations across names
  for (let i = 0; i < baseNames.length; i += 1) {
    for (let j = 0; j < baseNames.length; j += 1) {
      if (i === j) continue;
      const a = baseNames[i];
      const b = baseNames[j];
      addWithForms(candidates, `${a}${b}`, includeLeet);
      addWithForms(candidates, `${a}_${b}`, includeLeet);
      addWithForms(candidates, `${a}.${b}`, includeLeet);
      addWithForms(candidates, `${a}@${b}`, includeLeet);
      addWithSuffixes(candidates, `${a}${b}`, ["123", "2024", "786", "007"], includeLeet);
    }
  }

  // 4) Location and interest standalone patterns
  baseLocations.forEach((loc) => addWithSuffixes(candidates, loc, suffixPool, includeLeet));
  baseInterests.forEach((interest) => addWithSuffixes(candidates, interest, suffixPool, includeLeet));

  // 5) Phone-based patterns
  phones.forEach((phone) => {
    candidates.add(phone);
    baseNames.forEach((name) => {
      addWithForms(candidates, `${name}${phone}`, includeLeet);
      addWithForms(candidates, `${phone}${name}`, includeLeet);
      addWithForms(candidates, `${name}@${phone}`, includeLeet);
    });
  });

  // 6) Explicit symbol swaps for human-style habits
  baseNames.forEach((name) => {
    addWithForms(candidates, name.replace(/a/g, "@"), includeLeet);
    addWithForms(candidates, name.replace(/i/g, "!"), includeLeet);
    addWithForms(candidates, name.replace(/o/g, "0"), includeLeet);
    addWithForms(candidates, name.replace(/s/g, "$"), includeLeet);
  });

  // 7) Router default patterns
  if (includeRouterDefaults) {
    addRouterDefaults(candidates, includeLeet);
  }

  // 8) Repeated patterns
  baseNames.forEach((name) => {
    addWithForms(candidates, `${name}${name}`, includeLeet);
    addWithForms(candidates, `${name}123${name}`, includeLeet);
    addWithForms(candidates, `${name}@123${name}`, includeLeet);
    addWithSuffixes(candidates, `${name}${name}`, ["123", "786", "2024"], includeLeet);
  });

  const topUpAdded = topUpCandidates(
    candidates,
    requestedSize,
    [...baseNames, ...baseLocations, ...baseInterests, ...dobList],
    includeLeet
  );
  if (topUpAdded > 0) {
    warnings.push(`Top-up added ${topUpAdded} extra pattern candidates.`);
  } else if (requestedSize > candidates.size) {
    warnings.push("Could not fully reach requested size without adding non-target generic seeds.");
  }

  const uniquePasswords = [...candidates]
    .filter(Boolean)
    .sort((a, b) => (a.length - b.length) || a.localeCompare(b));
  const totalUnique = uniquePasswords.length;
  const finalList = uniquePasswords.slice(0, requestedSize);

  const clippedByLimit = requestedRaw > HARD_LIMIT;
  const clippedByCandidates = requestedSize > totalUnique;

  return {
    passwords: finalList,
    generatedCount: finalList.length,
    requestedRaw,
    requestedSize,
    hardLimit: HARD_LIMIT,
    totalUnique,
    clippedByLimit,
    clippedByCandidates,
    warnings
  };
}
