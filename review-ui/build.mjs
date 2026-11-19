import { build } from 'esbuild';
import { readFileSync, writeFileSync } from 'node:fs';
const output=await build({entryPoints:['review.js'],bundle:true,write:false,format:'iife',platform:'browser',target:'es2022',minify:true,legalComments:'inline'});
const script=output.outputFiles[0].text.replaceAll('</script','<\\/script');
writeFileSync('../src/ankiplusmcp/review_ui/review.html',readFileSync('review.template.html','utf8').replace('__BUNDLE__',()=>script));
