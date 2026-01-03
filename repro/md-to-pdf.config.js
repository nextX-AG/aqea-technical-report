// md-to-pdf config for a clean, paper-like PDF.
// Keep deterministic: no remote assets.

const path = require("path");

module.exports = {
  stylesheet: [path.join(__dirname, "pdf.css")],
  // Some Linux environments (e.g. hardened Ubuntu / AppArmor) block Chromium sandboxing.
  // For CI/containers, --no-sandbox is the pragmatic workaround.
  launch_options: {
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  },
  pdf_options: {
    format: "A4",
    printBackground: true,
    margin: {
      top: "18mm",
      bottom: "18mm",
      left: "16mm",
      right: "16mm",
    },
  },
};

