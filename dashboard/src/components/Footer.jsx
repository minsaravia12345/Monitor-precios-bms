import { IconGithub, IconSparkle } from './Icons';

export default function Footer({ ultimaActualizacion, totalVisible, totalGeneral }) {
  return (
    <footer className="app-footer">
      <span>
        Mostrando {totalVisible} de {totalGeneral} productos monitoreados · Price Index, Promo Pressure,
        Visibility Index y MOS son estimaciones internas
        {ultimaActualizacion ? ` · Última sincronización: ${ultimaActualizacion}` : ''}
      </span>
      <div className="app-footer-links">
        <span className="footer-credit">
          <IconSparkle />
          Hecho con Súper IA
        </span>
        <a href="https://github.com/minsaravia12345/Monitor-precios-bms" target="_blank" rel="noreferrer">
          <IconGithub />
          Repositorio del proyecto
        </a>
      </div>
    </footer>
  );
}
