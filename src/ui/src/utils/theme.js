import { createTheme } from "@mui/material/styles";

export const lightTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#4d90fe",
    },
    background: {
      default: "#f9f9f9",
      paper: "#ffffff",
    },
    text: {
      primary: "#121212",
    },
    error: {
      main: "#ff4c4c",
    },
    divider: "#cccccc",
  },
});

export const darkTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#4d90fe",
    },
    background: {
      default: "#1a1a1a",
      paper: "#121212",
    },
    text: {
      primary: "#e0e0e0",
    },
    error: {
      main: "#ff4c4c",
    },
    divider: "#444444",
  },
});
