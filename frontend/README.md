# FundamenTracker Frontend

This directory contains the React-based frontend for FundamenTracker, built with Vite and TypeScript. It serves as the primary user interface for monitoring stocks, managing alerts, and viewing AI valuations.

## Tech Stack

- **Framework:** React 18
- **Build Tool:** Vite
- **Language:** TypeScript
- **Styling:** CSS Variables with Dark Mode by default.
- **Charts:** Recharts for rendering historical fundamental metrics and price action.
- **Icons:** Lucide React

## Project Structure

- `src/components/`: Modular React components.
  - `WatchlistSection.tsx`: Manages the overall grid/table layout, market overview, and tags.
  - `TickerCard.tsx`: Grid-view component for individual stocks.
  - `TickerRow.tsx`: Table-view component for individual stocks.
  - `LineChartModal.tsx` & `InlineChart.tsx`: Recharts-based components for rendering historical metrics.
- `src/index.css`: Global styles, CSS tokens, and layout variables.
- `src/App.tsx`: Main application entry point.

## Environment Variables

For the frontend to communicate with the backend, you must configure the API URL. In production (like Vercel), set this in your deployment dashboard. For local development, create a `.env.local` file in this directory:

```env
VITE_API_URL=http://localhost:8000
```

*(Note: In Docker Compose, the backend runs on port 8000 by default).*

## Running Locally

To run the frontend independently of Docker (e.g., for faster HMR during UI development):

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```

The application will be available at `http://localhost:5173`.

## UI/UX Notes

- **Dynamic Updates:** The UI listens for custom events (like `tagsUpdated`) to sync state across the application without requiring a full page refresh.
- **AI Valuations:** Stock analysis is requested directly from the backend (which uses the Gemini API) and rendered dynamically below the ticker rows or inside the cards.
