const toCamelCase = (str) => {
  if (!str) return "";
  if (typeof str !== "string") {
    console.warn("toCamelCase received non-string input:", str);
    return str;
  }
  if (!str.match(/[_\s]/)) {
    // If there are no underscores or spaces, assume it's already camelCase or a single word
    return str;
  }
  return str
    .toLowerCase()
    .split(/[_\s]+/)
    .map((word, index) =>
      index === 0 ? word : word.charAt(0).toUpperCase() + word.slice(1),
    )
    .join("");
};

const toSnakeCase = (str) => {
  return str
    .replace(/([A-Z])/g, "_$1")
    .toLowerCase()
    .replace(/^_/, ""); // Remove leading underscore if it exists
};

export { toCamelCase, toSnakeCase };
