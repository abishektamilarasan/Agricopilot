import "./globals.css";
import { FieldProvider } from "./components/FieldContext";


export const metadata = {
  title: "AgriCopilot - Agricultural AI Decision Intelligence",
  description:
    "A multimodal AI copilot that reasons across weather, soil, satellite, and market data to generate interpretable agricultural recommendations with confidence estimates.",
  keywords: "agriculture, AI, farming, crop management, decision intelligence, food security",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <FieldProvider>
        <div className="app-container">
          <nav className="navbar">
            <a href="/" className="navbar-brand">
              <img src="/logo.png" alt="Logo" className="logo-icon" style={{width: "48px", height: "48px", borderRadius: "6px"}} />
              <h1>AgriCopilot</h1>
            </a>

            
            <ul className="navbar-links">
              <li>
                <a href="/" id="nav-dashboard">
                  🧭 Command Center
                </a>
              </li>
              <li>
                <a href="/chat" id="nav-chat">
                  💬 Copilot
                </a>
              </li>
              <li>
                <a href="/crop-doctor" id="nav-crop-doctor">
                  🩺 Crop Doctor
                </a>
              </li>
              <li>
                <a href="/model-performance" id="nav-model-performance">
                  🧪 ML Models
                </a>
              </li>
            </ul>


            <div className="navbar-status">
              <span className="status-dot connected" id="status-indicator"></span>
              <span id="status-text">System Online</span>
            </div>
          </nav>

          <main className="main-content">{children}</main>
        </div>
      </FieldProvider>
      </body>
    </html>
  );
}
