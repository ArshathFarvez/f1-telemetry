export const SUPPORTED_SEASONS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];

const VERSTAPPEN_DRIVER_NUMBER_BY_SEASON = {
  2018: "33",
  2019: "33",
  2020: "33",
  2021: "33",
  2022: "1",
  2023: "1",
  2024: "1",
  2025: "1",
  2026: "3",
};

const VERSTAPPEN_TEAMMATE_BY_SEASON = {
  2018: "RIC",
  2019: "GAS",
  2020: "ALB",
  2021: "PER",
  2022: "PER",
  2023: "PER",
  2024: "PER",
  2025: "TSU",
  2026: "HAD",
};

function normalizeSeason(year) {
  const season = Number.parseInt(year, 10);
  return SUPPORTED_SEASONS.includes(season) ? season : 2026;
}

export function verstappenDriverNumber(year) {
  return VERSTAPPEN_DRIVER_NUMBER_BY_SEASON[normalizeSeason(year)];
}

export function verstappenTeammate(year) {
  return VERSTAPPEN_TEAMMATE_BY_SEASON[normalizeSeason(year)];
}

export function telemetryDriverId(code, year) {
  return code === "VER" ? verstappenDriverNumber(year) : code;
}
