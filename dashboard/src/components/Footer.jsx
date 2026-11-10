import { IconGithub } from './Icons';

export default function Footer({ ultimaActualizacion, totalVisible, totalGeneral }) {
  return (
    <footer className="app-footer">
      <span>
        Mostrando {totalVisible} de {totalGeneral} productos monitoreados
        {ultimaActualizacion ? ` · Última sincronización: ${ultimaActualizacion}` : ''}
      </span>
      <a href="https://github.com/minsaravia12345/Monitor-precios-bms" target="_blank" rel="noreferrer">
        <IconGithub />
        Código en GitHub
      </a>
    </footer>
  );
}
