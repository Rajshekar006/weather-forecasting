const form = document.getElementById("search-form");
const placeInput = document.getElementById("place-input");
const searchBtn = document.getElementById("search-btn");
const btnText = searchBtn.querySelector(".btn-text");
const btnSpinner = searchBtn.querySelector(".btn-spinner");
const errorBanner = document.getElementById("error-banner");
const results = document.getElementById("results");
const emptyState = document.getElementById("empty-state");
const dailyForecast = document.getElementById("daily-forecast");
const suggestions = document.getElementById("suggestions");
const placePicker = document.getElementById("place-picker");
const placeOptions = document.getElementById("place-options");

let suggestTimer = null;
let activeSuggestion = -1;

function setLoading(isLoading) {
  searchBtn.disabled = isLoading;
  btnText.classList.toggle("hidden", isLoading);
  btnSpinner.classList.toggle("hidden", !isLoading);
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
}

function hideError() {
  errorBanner.classList.add("hidden");
  errorBanner.textContent = "";
}

function hideSuggestions() {
  suggestions.innerHTML = "";
  suggestions.classList.add("hidden");
  activeSuggestion = -1;
}

function hidePlacePicker() {
  placePicker.classList.add("hidden");
  placeOptions.innerHTML = "";
}

function formatValue(value, suffix = "") {
  if (value === null || value === undefined) return "N/A";
  return `${Math.round(value)}${suffix}`;
}

function formatTime(isoString, timezone) {
  if (!isoString) return "";
  try {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZone: timezone || undefined,
    });
  } catch {
    return isoString;
  }
}

function renderWeather(data) {
  const { location, current, daily } = data;

  document.getElementById("location-name").textContent =
    location.label || location.name;
  document.getElementById("location-meta").textContent = [
    location.place_type,
    `${location.latitude?.toFixed(2)}°, ${location.longitude?.toFixed(2)}°`,
  ]
    .filter(Boolean)
    .join(" · ");
  document.getElementById("current-time").textContent =
    `Updated ${formatTime(current.time, location.timezone)}`;

  document.getElementById("current-icon").textContent = current.icon;
  document.getElementById("current-temp").textContent = formatValue(current.temperature);
  document.getElementById("current-label").textContent = current.label;

  document.getElementById("feels-like").textContent =
    `${formatValue(current.feels_like)}°C`;
  document.getElementById("humidity").textContent =
    `${formatValue(current.humidity)}%`;
  document.getElementById("wind").textContent =
    `${formatValue(current.wind_speed)} km/h ${current.wind_direction}`;
  document.getElementById("precipitation").textContent =
    `${current.precipitation ?? 0} mm`;

  dailyForecast.innerHTML = daily
    .map(
      (day) => `
      <div class="day-card">
        <p class="day-name">${day.day_name}</p>
        <p class="day-date">${day.date.slice(5)}</p>
        <div class="day-icon">${day.icon}</div>
        <p class="day-label">${day.label}</p>
        <p class="day-temps">
          ${formatValue(day.temp_max)}°
          <span class="min">/ ${formatValue(day.temp_min)}°</span>
        </p>
        ${
          day.precip_prob != null
            ? `<p class="day-precip">${day.precip_prob}% rain</p>`
            : ""
        }
      </div>
    `
    )
    .join("");

  emptyState.classList.add("hidden");
  placePicker.classList.add("hidden");
  results.classList.remove("hidden");
}

function renderSuggestions(places) {
  if (!places.length) {
    hideSuggestions();
    return;
  }

  suggestions.innerHTML = places
    .map(
      (place, index) => `
      <li
        class="suggestion-item"
        role="option"
        data-index="${index}"
        data-lat="${place.latitude}"
        data-lon="${place.longitude}"
        data-label="${place.label.replace(/"/g, "&quot;")}"
      >
        <span class="suggestion-name">${place.label}</span>
        <span class="suggestion-type">${place.place_type || "place"}</span>
      </li>
    `
    )
    .join("");

  suggestions.classList.remove("hidden");
  activeSuggestion = -1;

  suggestions.querySelectorAll(".suggestion-item").forEach((item) => {
    item.addEventListener("mousedown", (event) => {
      event.preventDefault();
      selectPlace({
        latitude: parseFloat(item.dataset.lat),
        longitude: parseFloat(item.dataset.lon),
        label: item.dataset.label,
      });
    });
  });
}

function renderPlacePicker(places) {
  placeOptions.innerHTML = places
    .map(
      (place) => `
      <button
        type="button"
        class="place-option"
        data-lat="${place.latitude}"
        data-lon="${place.longitude}"
        data-label="${place.label.replace(/"/g, "&quot;")}"
      >
        <span class="place-option-name">${place.label}</span>
        <span class="place-option-type">${place.place_type || "place"}</span>
      </button>
    `
    )
    .join("");

  placePicker.classList.remove("hidden");
  results.classList.add("hidden");

  placeOptions.querySelectorAll(".place-option").forEach((button) => {
    button.addEventListener("click", () => {
      selectPlace({
        latitude: parseFloat(button.dataset.lat),
        longitude: parseFloat(button.dataset.lon),
        label: button.dataset.label,
      });
    });
  });
}

async function fetchPlaces(query) {
  const response = await fetch(`/api/places?q=${encodeURIComponent(query)}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Unable to search places.");
  }
  return data.places;
}

async function fetchWeatherByCoords(latitude, longitude) {
  hideError();
  hideSuggestions();
  setLoading(true);

  try {
    const response = await fetch(
      `/api/weather?lat=${latitude}&lon=${longitude}`
    );
    const data = await response.json();

    if (!response.ok) {
      showError(data.error || "Something went wrong.");
      return;
    }

    renderWeather(data);
  } catch (error) {
    showError(error.message || "Network error. Check your connection and try again.");
  } finally {
    setLoading(false);
  }
}

async function selectPlace(place) {
  placeInput.value = place.label;
  hideSuggestions();
  hidePlacePicker();
  await fetchWeatherByCoords(place.latitude, place.longitude);
}

async function searchPlaces(query) {
  hideError();
  hideSuggestions();
  hidePlacePicker();
  setLoading(true);

  try {
    const places = await fetchPlaces(query);

    if (places.length === 1) {
      await selectPlace(places[0]);
      return;
    }

    renderPlacePicker(places);
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false);
  }
}

placeInput.addEventListener("input", () => {
  clearTimeout(suggestTimer);
  const query = placeInput.value.trim();

  if (query.length < 2) {
    hideSuggestions();
    return;
  }

  suggestTimer = setTimeout(async () => {
    try {
      const places = await fetchPlaces(query);
      renderSuggestions(places.slice(0, 6));
    } catch {
      hideSuggestions();
    }
  }, 300);
});

placeInput.addEventListener("keydown", (event) => {
  const items = suggestions.querySelectorAll(".suggestion-item");
  if (!items.length || suggestions.classList.contains("hidden")) return;

  if (event.key === "ArrowDown") {
    event.preventDefault();
    activeSuggestion = Math.min(activeSuggestion + 1, items.length - 1);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    activeSuggestion = Math.max(activeSuggestion - 1, 0);
  } else if (event.key === "Enter" && activeSuggestion >= 0) {
    event.preventDefault();
    items[activeSuggestion].dispatchEvent(new MouseEvent("mousedown"));
    return;
  } else if (event.key === "Escape") {
    hideSuggestions();
    return;
  } else {
    return;
  }

  items.forEach((item, index) => {
    item.classList.toggle("active", index === activeSuggestion);
  });
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".input-wrap")) {
    hideSuggestions();
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = placeInput.value.trim();
  if (query) searchPlaces(query);
});

document.querySelectorAll(".quick-place").forEach((button) => {
  button.addEventListener("click", () => {
    const query = button.dataset.query;
    placeInput.value = query;
    searchPlaces(query);
  });
});
