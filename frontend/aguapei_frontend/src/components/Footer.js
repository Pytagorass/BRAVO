import React from "react";

function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="mt-auto py-3 border-top bg-light">
      <div className="container d-flex flex-column flex-md-row justify-content-between align-items-center gap-2">
        <div className="text-muted small text-center text-md-start">
          © {currentYear} BRAVO – Barco-hotel Reservas, Acomodações, Viagens e Operações.
        </div>
        <div className="text-muted small text-center text-md-end">
          Desenvolvido por Sergio Pytagoras Constantini ·{" "}
          <a
            href="https://github.com/Pytagorass"
            target="_blank"
            rel="noopener noreferrer"
          >
            github.com/Pytagorass
          </a>
        </div>
      </div>
    </footer>
  );
}

export default Footer;