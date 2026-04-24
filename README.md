# Landing web para Establecimientos OBI

Esta carpeta contiene una landing estatica de una sola pagina, pensada para
promocionar los servicios de Establecimientos OBI para confeccionistas de
indumentaria y salir bien parada en SEO desde el arranque.

## Archivos principales

- `index.html`: contenido, estructura semantica y metadatos SEO.
- `styles.css`: diseno responsive y visual.
- `script.js`: menu mobile, animaciones suaves y detalles simples.
- `gracias.html`: pagina de confirmacion para el formulario.
- `netlify.toml`: configuracion basica para publicar en Netlify.
- `VIDEO-GUIA.md`: guiones y orientacion para producir los 3 videos.
- `robots.txt`: directiva para buscadores.
- `sitemap.xml`: mapa del sitio.

## Antes de publicar

1. Reemplazar los SVG de servicio por fotos o thumbnails reales.
2. Exportar y subir los 3 videos finales con voz.
3. Completar direccion fisica si quieren reforzar SEO local en Google Business.
4. Verificar el formulario desde Netlify una vez online.
5. Medir indexacion y consultas desde Search Console.

## Recomendaciones SEO importantes

- Agregar una ciudad o zona real en el `title`, la `meta description` y al
  menos un subtitulo si luego quieren priorizar una localidad mas especifica.
- Crear o completar la ficha de Google Business Profile del negocio.
- Subir fotos reales del taller o de las piezas con nombres descriptivos.
- Conseguir menciones o enlaces desde Instagram, directorios y clientes.
- Dar de alta Search Console y enviar el sitemap luego del deploy.

## Publicacion simple

La opcion prioritaria para este proyecto es Netlify:

1. Crear una cuenta en Netlify.
2. Crear un sitio nuevo y subir esta carpeta.
3. Verificar que el sitio publique bien con la URL temporal de Netlify.
4. Agregar `obicint.com.ar` como dominio personalizado.
5. Copiar los nameservers que te indique Netlify.
6. Cargarlos en NIC Argentina dentro de `Delegaciones`.

Como el sitio es estatico, no necesita servidor complejo. Eso ayuda a la
velocidad y al SEO.
