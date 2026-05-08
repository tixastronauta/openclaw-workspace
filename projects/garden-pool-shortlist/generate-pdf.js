const fs = require('fs');
const path = require('path');
const PDFDocument = require('pdfkit');

const outDir = path.join(__dirname, 'data');
const imgDir = path.join(outDir, 'images');
fs.mkdirSync(imgDir, { recursive: true });

const products = [
  {
    rank: 1,
    name: 'MaxMat — Bestway Steel Pro Max 366×100 cm',
    price: '199 €',
    dimensions: 'Ø366 × 100 cm',
    capacity: '9.150 L',
    includes: 'Bomba filtrante, cartucho e escada de segurança',
    stock: 'Aparecia sem stock no momento da pesquisa',
    verdict: 'Melhor preço encontrado; compra excelente se voltar a ter stock.',
    link: 'https://www.maxmat.pt/pt/bestway/piscina-redonda-366x100cm-metal_p31473.html',
    image: 'https://www.maxmat.pt/temp/JPG_ad77c8450cd840ee35f11b8688ceb075.png'
  },
  {
    rank: 2,
    name: 'KuantoKusta / Amazon ES — Intex Prism Frame 366×99 cm',
    price: 'desde ~189,67 €',
    dimensions: 'Ø366 × 99 cm',
    capacity: '8.592 L',
    includes: 'Depuradora de cartucho 2.006 L/h e escada',
    stock: 'Comparador; confirmar vendedor, portes e disponibilidade',
    verdict: 'Muito forte em preço/profundidade; boa alternativa à Bestway.',
    link: 'https://www.kuantokusta.pt/p/10171005/intex-piscina-desmontavel-26716-366-x-99-x-366-s8901636',
    image: 'https://www.intex.pt/74701-thickbox_default/26716NP-piscina-elevada-redonda-prism-frame-com-bomba.jpg'
  },
  {
    rank: 3,
    name: 'Pools.shop — Bestway Steel Pro Max 366×100 cm',
    price: '234,99 €',
    dimensions: 'Ø366 × 100 cm',
    capacity: '9,15 m³',
    includes: 'Bomba de filtro 2.006 L/h, cartucho, escada e remendo',
    stock: 'Em stock na pesquisa',
    verdict: 'Compra segura se queres preço baixo sem esperar pelo stock da MaxMat.',
    link: 'https://www.pools.shop/pt-PT/bestway/frame-pool-set-steel-pro-max-oe-366-x-100-cm-incl-bomba-de',
    image: 'https://ap.nice-cdn.com/upload/image/product/large/default/bestway-frame-pool-set-steel-pro-max-o-366-x-100-cm-incl-bomba-de-filtro-1-st-772200-pt.jpg'
  },
  {
    rank: 4,
    name: 'Bestway Store PT — Bestway Steel Pro Max 366×100 cm',
    price: '296,35 €',
    dimensions: 'Ø366 × 100 cm',
    capacity: '9.150 L',
    includes: 'Bomba 2.006 L/h, cartucho e escada',
    stock: 'Loja oficial; portes grátis acima de 60 € para Portugal Continental',
    verdict: 'Mais caro, mas loja oficial e garantia/entrega mais previsíveis.',
    link: 'https://bestwaystore.pt/1378-conjunto-de-piscina-desmontavel-bestway-steel-pro-max-de-366-m-x-100-m/',
    image: 'https://bestwaystore.pt/wp-content/uploads/2024/03/6942138986211-min.jpg'
  },
  {
    rank: 5,
    name: 'Amazon.es — Bestway Steel Pro Max 366×100 cm',
    price: '~230,99 €',
    dimensions: 'Ø366 × 100 cm',
    capacity: '9.150 L aprox.',
    includes: 'Normalmente bomba + escada; confirmar no anúncio exato',
    stock: 'Confirmar portes para Portugal e vendedor',
    verdict: 'Boa se aparecer com envio barato; atenção a marketplace e devoluções.',
    link: 'https://www.amazon.es/s?k=Bestway+Steel+Pro+Max+366x100',
    image: 'https://bestwaystore.pt/wp-content/uploads/2024/03/6942138986211-min.jpg'
  },
  {
    rank: 6,
    name: 'Decathlon — Bestway Steel Pro Max 457×122 cm',
    price: '395 €',
    dimensions: 'Ø457 × 122 cm',
    capacity: '16.015 L aprox.',
    includes: 'Depuradora/filtro e escada',
    stock: 'Confirmar no site Decathlon',
    verdict: 'Já é piscina adulta a sério; boa profundidade, mas ocupa bastante espaço.',
    link: 'https://www.decathlon.pt/p/piscina-steel-pro-max-circular-457x122cm-com-depuradora-filtro-escada/X8898854/m8898854',
    image: 'https://cdn.juguetilandia.com/images/articulos/9595g00.jpg'
  },
  {
    rank: 7,
    name: 'Intex PT — Intex Prism Frame 400×200×122 cm',
    price: '~508–551 €',
    dimensions: '400 × 200 × 122 cm',
    capacity: '8.418 L',
    includes: 'Depuradora 2.006 L/h, filtro tipo A e escada',
    stock: 'Preço varia por loja; Intex mostra produto e especificações',
    verdict: 'A melhor forma para “mais funda do que comprida”: compacta e com 122 cm.',
    link: 'https://www.intex.pt/piscinas/desmontavel/55243-piscina-desmontavel-retangular-inte--prisma-frame-bomba',
    image: 'https://www.intex.pt/74906-thickbox_default/piscina-desmontavel-retangular-inte--prisma-frame-bomba.jpg'
  },
  {
    rank: 8,
    name: 'Bestway Store PT — Power Steel 412×201×122 cm',
    price: '571,95 €',
    dimensions: '412 × 201 × 122 cm',
    capacity: '8.124 L',
    includes: 'Bomba de cartucho 2.006 L/h, escada e dispensador ChemConnect',
    stock: 'Loja oficial; portes grátis acima de 60 €',
    verdict: 'Equivalente Bestway da opção Intex: compacta, funda e robusta.',
    link: 'https://bestwaystore.pt/1867-conjunto-de-piscina-desmontavel-bestway-power-steel-412-m-x-201-m-x-122-m/',
    image: 'https://bestwaystore.pt/wp-content/uploads/2024/03/56458@56456@56661@56457_26026_PR_WEB_150dpi-1024x683.jpg'
  },
  {
    rank: 9,
    name: 'Leroy Merlin — Intex 400×200×122 cm',
    price: '~551,50 €',
    dimensions: '400 × 200 × 122 cm',
    capacity: '8.418 L aprox.',
    includes: 'Bomba de filtro e escada',
    stock: 'Confirmar no site Leroy Merlin',
    verdict: 'Boa alternativa nacional à compra via Intex/Amazon; comparar portes.',
    link: 'https://www.leroymerlin.pt/produtos/piscina-retangular-400x200-122-cm-desmontavel-com-bomba-de-filtro-prism-frame-intex-82824254.html',
    image: 'https://www.intex.pt/74906-thickbox_default/piscina-desmontavel-retangular-inte--prisma-frame-bomba.jpg'
  },
  {
    rank: 10,
    name: 'Bestway Store PT — Steel Pro Max 549×122 cm',
    price: '591 €',
    dimensions: 'Ø549 × 122 cm',
    capacity: '23.062 L',
    includes: 'Bomba 5.678 L/h, escada, capa de inverno e remendo',
    stock: 'Em stock na pesquisa',
    verdict: 'Melhor €/litro, mas só faz sentido com bastante jardim e consumo de água.',
    link: 'https://bestwaystore.pt/2192-conjunto-de-piscina-desmontavel-redonda-steel-pro-max-da-bestway-549-x-122-cm/',
    image: 'https://bestwaystore.pt/wp-content/uploads/2025/01/6941607327814-5.jpg'
  }
];

async function downloadImage(url, file) {
  const target = path.join(imgDir, file);
  if (fs.existsSync(target) && fs.statSync(target).size > 1000) return target;
  try {
    const res = await fetch(url, { headers: { 'user-agent': 'Mozilla/5.0' } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    fs.writeFileSync(target, buf);
    return target;
  } catch (e) {
    console.error('Image failed:', url, e.message);
    return null;
  }
}

function euroNumber(price) {
  const m = price.match(/(\d+[,.]?\d*)/);
  return m ? Number(m[1].replace(',', '.')) : 999999;
}

function addPageHeader(doc, title = 'Piscinas de jardim — shortlist') {
  doc.fillColor('#0f172a').font('Helvetica-Bold').fontSize(10).text(title, 46, 26);
  doc.moveTo(46, 42).lineTo(549, 42).strokeColor('#cbd5e1').stroke();
}

function fitImage(doc, imgPath, x, y, maxW, maxH) {
  try {
    doc.image(imgPath, x, y, { fit: [maxW, maxH], align: 'center', valign: 'center' });
  } catch (e) {
    doc.roundedRect(x, y, maxW, maxH, 8).fillAndStroke('#f1f5f9', '#cbd5e1');
    doc.fillColor('#64748b').fontSize(9).text('Imagem indisponível', x + 10, y + maxH / 2 - 6, { width: maxW - 20, align: 'center' });
  }
}

(async () => {
  for (const p of products) p.imgPath = await downloadImage(p.image, `pool-${p.rank}${path.extname(new URL(p.image).pathname).split('?')[0] || '.jpg'}`);

  const outPath = path.join(outDir, 'top-10-piscinas-jardim-adultos-low-cost.pdf');
  const doc = new PDFDocument({ size: 'A4', margin: 46, info: { Title: 'Top 10 piscinas de jardim para adultos', Author: 'Nyx / OpenClaw' } });
  doc.pipe(fs.createWriteStream(outPath));

  // Cover
  doc.rect(0,0,595,842).fill('#f8fafc');
  doc.fillColor('#0f172a').font('Helvetica-Bold').fontSize(28).text('Top 10 piscinas de jardim', 46, 70, { width: 500 });
  doc.fontSize(17).fillColor('#334155').text('Adultos · low cost · mais fundo que comprido', 46, 108);
  doc.font('Helvetica').fontSize(10).fillColor('#475569').text('Pesquisa feita em lojas de especialidade em Portugal, supermercados/retalho e Amazon.es. Preços e stock devem ser confirmados antes de comprar.', 46, 142, { width: 500, lineGap: 3 });
  fitImage(doc, products[7].imgPath, 70, 205, 455, 260);
  doc.roundedRect(46, 510, 503, 145, 12).fillAndStroke('#ffffff', '#cbd5e1');
  doc.fillColor('#0f172a').font('Helvetica-Bold').fontSize(15).text('Resumo rápido', 70, 535);
  doc.font('Helvetica').fontSize(11).fillColor('#334155')
    .text('• Melhor compra low cost: #1–#3, modelos 366×99/100 cm.', 70, 565)
    .text('• Melhor compromisso adulto/fundura: #7 ou #8, 400/412×200×122 cm.', 70, 585)
    .text('• Se houver muito jardim: #10 dá imenso volume por euro, mas consome muita água.', 70, 605)
    .text('• Para segurança e conforto: prever base nivelada, tapete, cobertura, químicos e filtros.', 70, 625);
  doc.fillColor('#64748b').fontSize(9).text('Gerado em 2026-05-08', 46, 790);

  // Table
  doc.addPage(); addPageHeader(doc, 'Resumo comparativo');
  doc.fillColor('#0f172a').font('Helvetica-Bold').fontSize(18).text('Tabela comparativa', 46, 62);
  const rows = products.map(p => [String(p.rank), p.name.replace(/^[^—]+—\s*/, ''), p.price, p.dimensions, p.verdict]);
  const colX = [46, 74, 245, 318, 405];
  const widths = [22, 165, 65, 80, 144];
  let y = 100;
  doc.roundedRect(46, y - 7, 503, 24, 5).fill('#0f172a');
  ['#','Opção','Preço','Dimensões','Nota'].forEach((h,i)=>doc.fillColor('#fff').font('Helvetica-Bold').fontSize(8).text(h,colX[i],y,{width:widths[i]}));
  y += 28;
  for (const [i,row] of rows.entries()) {
    const h = 46;
    if (y + h > 790) { doc.addPage(); addPageHeader(doc, 'Resumo comparativo'); y = 70; }
    doc.roundedRect(46, y - 6, 503, h, 4).fill(i % 2 ? '#ffffff' : '#f1f5f9');
    row.forEach((cell,j)=>doc.fillColor('#0f172a').font(j===0?'Helvetica-Bold':'Helvetica').fontSize(7.3).text(cell, colX[j], y, { width: widths[j], height: h-4 }));
    y += h + 2;
  }

  // Cards
  for (const p of products) {
    doc.addPage(); addPageHeader(doc, `Opção #${p.rank}`);
    doc.fillColor('#0f172a').font('Helvetica-Bold').fontSize(18).text(`#${p.rank} ${p.name}`, 46, 62, { width: 503 });
    fitImage(doc, p.imgPath, 56, 105, 230, 170);
    doc.roundedRect(310, 105, 235, 170, 10).fillAndStroke('#ffffff', '#cbd5e1');
    let sy = 124;
    const fields = [
      ['Preço', p.price], ['Dimensões', p.dimensions], ['Capacidade', p.capacity], ['Inclui', p.includes], ['Stock/notas', p.stock]
    ];
    for (const [k,v] of fields) {
      doc.fillColor('#0f172a').font('Helvetica-Bold').fontSize(9).text(`${k}:`, 328, sy, { width: 70 });
      doc.fillColor('#334155').font('Helvetica').fontSize(9).text(v, 400, sy, { width: 125 });
      sy += doc.heightOfString(v, { width: 125, fontSize: 9 }) + 12;
    }
    doc.roundedRect(46, 305, 503, 95, 10).fillAndStroke('#ecfeff', '#67e8f9');
    doc.fillColor('#0e7490').font('Helvetica-Bold').fontSize(12).text('Veredicto Nyx', 66, 325);
    doc.fillColor('#164e63').font('Helvetica').fontSize(11).text(p.verdict, 66, 348, { width: 460, lineGap: 3 });
    doc.roundedRect(46, 425, 503, 100, 10).fillAndStroke('#fff', '#cbd5e1');
    doc.fillColor('#0f172a').font('Helvetica-Bold').fontSize(12).text('Link', 66, 446);
    doc.fillColor('#2563eb').font('Helvetica').fontSize(9).text(p.link, 66, 468, { width: 455, underline: true, link: p.link });
    doc.fillColor('#475569').fontSize(8.5).text('Nota: preços, stock, portes e acessórios podem mudar. Confirmar antes de comprar — lojas fazem magia negra com stock no verão.', 66, 548, { width: 455 });
  }

  // Final recommendation
  doc.addPage(); addPageHeader(doc, 'Recomendação final');
  doc.fillColor('#0f172a').font('Helvetica-Bold').fontSize(20).text('Recomendação final', 46, 70);
  doc.font('Helvetica').fontSize(11).fillColor('#334155').text(
    'Se o objetivo é gastar pouco e ter uma piscina usável por adultos, eu começava pelas opções 366×99/100 cm (#1 a #4). Já dão profundidade suficiente para estar dentro de água sem parecer piscina de bebé.',
    46, 110, { width: 503, lineGap: 4 }
  );
  doc.font('Helvetica-Bold').fillColor('#0f172a').text('Escolha equilibrada:', 46, 170);
  doc.font('Helvetica').fillColor('#334155').text('#3 Pools.shop Bestway 366×100 cm se quiseres comprar já com preço decente.', 46, 190, { width: 503 });
  doc.font('Helvetica-Bold').fillColor('#0f172a').text('Escolha mais adulta/funda:', 46, 230);
  doc.font('Helvetica').fillColor('#334155').text('#7 Intex 400×200×122 cm ou #8 Bestway 412×201×122 cm — mais caras, mas o formato faz mais sentido para o que pediste.', 46, 250, { width: 503 });
  doc.font('Helvetica-Bold').fillColor('#0f172a').text('Antes de comprar, medir:', 46, 300);
  doc.font('Helvetica').fillColor('#334155').text('• área nivelada disponível\n• acesso para entrega pesada\n• ponto de água e drenagem\n• onde guardar no inverno\n• custo extra de base, cobertura, cloro, filtros e aspirador simples', 66, 323, { width: 470, lineGap: 5 });

  doc.end();
  await new Promise(r => doc.on('end', r));
  console.log(outPath);
})();
