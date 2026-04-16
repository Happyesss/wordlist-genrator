import {
  COMMON_SUFFIXES,
  DEFAULT_PHONE_PATTERNS,
  DEFAULT_ROUTERS,
  HARD_LIMIT,
  HINGLISH_WORDS,
  MAX_TOTAL_NAMES,
  YEAR_END,
  YEAR_START
} from "./constants.js";
import {
  clampNumber,
  caseForms,
  sanitizeSize,
  unique
} from "./utils.js";

function buildRandomSuffixes(count) {
  const capped = clampNumber(count, 0, 200);
  const values = new Set();

  while (values.size < capped) {
    const candidate = Math.floor(Math.random() * 99999) + 1;
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

function addWithForms(set, base) {
  caseForms(base).forEach((item) => set.add(item));
}

function addWithSuffixes(set, base, suffixes) {
  const forms = caseForms(base);
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

function addYearCombos(set, base) {
  const forms = caseForms(base);
  forms.forEach((form) => {
    for (let year = YEAR_START; year <= YEAR_END; year += 1) {
      set.add(`${form}${year}`);
      set.add(`${form}@${year}`);
      set.add(`${form}#${year}`);
      set.add(`${form}!${year}`);
    }
  });
}

function addRouterDefaults(set) {
  DEFAULT_ROUTERS.forEach((router) => {
    addWithForms(set, router);
    set.add(router.replace("@", "#"));
    set.add(router.replace("@", "!"));
    set.add(router.replace("tp-link", "tplink"));
  });
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
    includeRandomNumbers,
    randomCount,
    desiredSize
  } = input;

  const names = unique([...owners, ...lastNames, ...family, ...pets]).slice(0, MAX_TOTAL_NAMES);
  if (names.length < owners.length + lastNames.length + family.length) {
    warnings.push(`Names were trimmed to first ${MAX_TOTAL_NAMES} entries for performance.`);
  }
  if (names.length === 0) {
    warnings.push("No names provided; using fallback base names.");
  }

  const baseNames = names.length ? names : ["owner", "admin", "guest"];
  const baseLocations = locations.length ? locations : ["city", "home"];
  const baseInterests = interests.length ? interests : ["wifi", "home"];
  const dobList = unique(exactDob.flatMap((dob) => dobVariants(dob)));
  const phones = unique([...DEFAULT_PHONE_PATTERNS, ...phoneNumbers]);
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
    addWithSuffixes(candidates, name, suffixPool);
    if (includeYears) {
      addYearCombos(candidates, name);
    }

    dobList.forEach((dob) => {
      addWithForms(candidates, `${name}${dob}`);
      addWithForms(candidates, `${name}@${dob}`);
      addWithForms(candidates, `${name}#${dob}`);
      addWithForms(candidates, `${name}!${dob}`);
    });
  });

  // 2) Name + location / interest patterns
  baseNames.forEach((name) => {
    baseLocations.forEach((loc) => {
      addWithForms(candidates, `${name}${loc}`);
      addWithForms(candidates, `${loc}${name}`);
      addWithForms(candidates, `${name}@${loc}`);
      addWithForms(candidates, `${loc}@${name}`);
      addWithSuffixes(candidates, `${name}${loc}`, ["123", "2024", "786"]);
    });

    baseInterests.forEach((interest) => {
      addWithForms(candidates, `${name}${interest}`);
      addWithForms(candidates, `${name}@${interest}`);
      addWithSuffixes(candidates, `${name}${interest}`, ["123", "2024", "786"]);
    });
  });

  // 3) Pair combinations across names
  for (let i = 0; i < baseNames.length; i += 1) {
    for (let j = 0; j < baseNames.length; j += 1) {
      if (i === j) continue;
      const a = baseNames[i];
      const b = baseNames[j];
      addWithForms(candidates, `${a}${b}`);
      addWithForms(candidates, `${a}_${b}`);
      addWithForms(candidates, `${a}.${b}`);
      addWithForms(candidates, `${a}@${b}`);
      addWithSuffixes(candidates, `${a}${b}`, ["123", "2024", "786", "007"]);
    }
  }

  // 4) Hinglish and cultural defaults
  HINGLISH_WORDS.forEach((word) => {
    addWithSuffixes(candidates, word, ["123", "2024", "2025", "786"]);
    addWithForms(candidates, `${word}India`);
    addWithForms(candidates, `${word}Noida`);
  });

  // 5) Location and interest standalone patterns
  baseLocations.forEach((loc) => addWithSuffixes(candidates, loc, suffixPool));
  baseInterests.forEach((interest) => addWithSuffixes(candidates, interest, suffixPool));

  // 6) Phone-based patterns
  phones.forEach((phone) => {
    candidates.add(phone);
    baseNames.forEach((name) => {
      addWithForms(candidates, `${name}${phone}`);
      addWithForms(candidates, `${phone}${name}`);
      addWithForms(candidates, `${name}@${phone}`);
    });
  });

  // 7) Router default patterns
  if (includeRouterDefaults) {
    addRouterDefaults(candidates);
  }

  // 8) Repeated patterns
  baseNames.forEach((name) => {
    addWithForms(candidates, `${name}${name}`);
    addWithForms(candidates, `${name}123${name}`);
    addWithForms(candidates, `${name}@123${name}`);
    addWithSuffixes(candidates, `${name}${name}`, ["123", "786", "2024"]);
  });

  const uniquePasswords = [...candidates].filter(Boolean);
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
