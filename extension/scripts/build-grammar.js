// In file: extension/scripts/build-grammar.js

const fs = require("fs");
const path = require("path");

console.log("Building ValuaScript grammar...");

// --- Define Paths ---
const projectRoot = path.join(__dirname, ".."); // The 'extension' directory
const specPath = path.join(projectRoot, "language-spec.json");
const templatePath = path.join(
  projectRoot,
  "syntaxes",
  "valuascript.tmLanguage.template.json"
);
const outputPath = path.join(
  projectRoot,
  "syntaxes",
  "valuascript.tmLanguage.json"
);

// --- Read Source Files ---
try {
  const specContent = fs.readFileSync(specPath, "utf8");
  const languageSpec = JSON.parse(specContent);

  let templateContent = fs.readFileSync(templatePath, "utf8");

  // --- Generate Regex from Spec ---
  // We sort by length descending to ensure longer keywords (if any) are matched first.
  const directivesRegex = languageSpec.directives
    .sort((a, b) => b.length - a.length)
    .join("|");
  const keywordsRegex = languageSpec.keywords
    .sort((a, b) => b.length - a.length)
    .join("|");
  const functionsRegex = languageSpec.functions
    .sort((a, b) => b.length - a.length)
    .join("|");

  // --- Replace Placeholders in Template ---
  templateContent = templateContent.replace(/__DIRECTIVES__/g, directivesRegex);
  templateContent = templateContent.replace(/__KEYWORDS__/g, keywordsRegex);
  templateContent = templateContent.replace(/__FUNCTIONS__/g, functionsRegex);

  // --- Write Final Grammar File ---
  fs.writeFileSync(outputPath, templateContent);

  console.log("ValuaScript grammar built successfully!");
} catch (error) {
  console.error("Error building grammar:", error);
  process.exit(1);
}
