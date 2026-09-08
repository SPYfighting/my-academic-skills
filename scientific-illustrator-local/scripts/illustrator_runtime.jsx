/* Scientific Illustrator Local — MIT.
 * Native path / text writing adapts Cell-lct's COM + JSX approach (yrui-cmd).
 * Config is a JSON object literal supplied by the trusted local Python adapter.
 * No eval of downloaded SVG, cache files, or Illustrator note strings.
 */
(function () {
    if (typeof SCIENTIFIC_VECTOR_CONFIG === 'undefined') return 'ERROR|NO_CONFIG';
    var c = SCIENTIFIC_VECTOR_CONFIG;
    function fail(message) { throw new Error(message); }
    function validNumber(x) { return typeof x === 'number' && isFinite(x) && Math.abs(x) < 1e10; }
    function samePath(a,b) {
        a=String(a);b=String(b);
        if(c.windows) {a=a.replace(/\\/g,'/').toLowerCase();b=b.replace(/\\/g,'/').toLowerCase();}
        return a===b;
    }
    function findDoc() {
        var found = null;
        for (var i=0; i<app.documents.length; i++) {
            var matches = app.documents[i].name === c.documentName;
            if(c.documentPath) {
                matches=false;
                try { matches=samePath(app.documents[i].fullName.fsName,new File(c.documentPath).fsName); } catch(ignoreUnsaved) {}
            }
            if (matches) {
                if (found !== null) fail('AMBIGUOUS_DOCUMENT_NAME');
                found = app.documents[i];
            }
        }
        if (found === null) fail('TARGET_DOCUMENT_CLOSED');
        return found;
    }
    function group(container, wanted) {
        for (var i=0; i<container.groupItems.length; i++) {
            var q=container.groupItems[i];
            if (q.name === wanted && q.parent === container) return q;
        }
        return null;
    }
    function rootOf(doc,name) {
        for (var i=0; i<doc.layers.length; i++) {
            var g=group(doc.layers[i], name||c.rootName);
            if (g !== null) return g;
        }
        return null;
    }
    function batchParent(doc,root,atoms,create) {
        if(!c.textOnTop || !atoms.length || atoms[0].kind!=='text') return root;
        for(var i=0;i<atoms.length;i++) if(atoms[i].kind!=='text') fail('MIXED_TEXT_BATCH');
        var tr=rootOf(doc,c.rootName+'_text');
        if(tr!==null) {parseRoot(tr);return tr;}
        if(!create) fail('TEXT_LAYER_MISSING');
        var layer=doc.layers.add();layer.name='Editable text '+c.rootName.substring(4);
        tr=layer.groupItems.add();tr.name=c.rootName+'_text';tr.note=root.note;
        return tr;
    }
    function parseRoot(root) {
        var p=String(root.note).split('|');
        if (p.length !== 5 || p[0] !== 'scientific-vector-local' || p[1] !== c.cacheHash) fail('ROOT_PROVENANCE_MISMATCH');
        var v={left:Number(p[2]),top:Number(p[3]),scale:Number(p[4])};
        if (!validNumber(v.left)||!validNumber(v.top)||!validNumber(v.scale)||v.scale<=0) fail('BAD_ROOT_TRANSFORM');
        return v;
    }
    function intersects(a,b,margin) {
        return !(a[2]+margin<=b[0] || a[0]-margin>=b[2] || a[3]-margin>=b[1] || a[1]+margin<=b[3]);
    }
    function choosePlacement(doc) {
        var box=doc.artboards[doc.artboards.getActiveArtboardIndex()].artboardRect;
        var width=box[2]-box[0],height=box[1]-box[3];
        var scale=Math.min(width*c.maxWidthFraction/c.viewBox[2],height*c.maxHeightFraction/c.viewBox[3]);
        var w=c.viewBox[2]*scale,h=c.viewBox[3]*scale;
        var existing=[];
        for (var i=0;i<doc.pageItems.length;i++) {
            var item=doc.pageItems[i];
            if (!item.hidden) {
                try { existing.push(item.visibleBounds); } catch (ignoreBounds) {}
            }
        }
        var positions=[[0.5,0.5],[0,0],[1,0],[0,1],[1,1],[0.5,0],[0,0.5],[1,0.5],[0.5,1]];
        for (var j=0;j<positions.length;j++) {
            var left=box[0]+(width-w)*positions[j][0],top=box[1]-(height-h)*positions[j][1];
            var candidate=[left,top,left+w,top-h];
            var clear=true;
            for (var k=0;k<existing.length;k++) if (intersects(candidate,existing[k],4)) {clear=false;break;}
            if (clear || c.allowOverlap) return {left:left,top:top,scale:scale};
        }
        fail('NO_CLEAR_SPACE: use a blank artboard or explicitly authorize overlap');
    }
    function rgb(a) {
        var color=new RGBColor(); color.red=a[0];color.green=a[1];color.blue=a[2];return color;
    }
    function mapped(point,t) {
        return [t.left+(point[0]-c.viewBox[0])*t.scale,t.top-(point[1]-c.viewBox[1])*t.scale];
    }
    function paint(a,path,t) {
        path.filled=a.fill!==null;
        if (path.filled) path.fillColor=rgb(a.fill);
        path.stroked=a.stroke!==null;
        path.evenodd=a.fill_rule==='evenodd';
        if (path.stroked) {
            path.strokeColor=rgb(a.stroke); path.strokeWidth=a.stroke_width*t.scale;
            path.strokeCap=a.linecap==='round'?StrokeCap.ROUNDENDCAP:(a.linecap==='square'?StrokeCap.PROJECTINGENDCAP:StrokeCap.BUTTENDCAP);
            path.strokeJoin=a.linejoin==='round'?StrokeJoin.ROUNDENDJOIN:(a.linejoin==='bevel'?StrokeJoin.BEVELENDJOIN:StrokeJoin.MITERENDJOIN);
            path.strokeMiterLimit=a.miter;
            var dashes=[];
            for(var i=0;i<a.dashes.length;i++) dashes.push(a.dashes[i]*t.scale);
            if(dashes.length%2) dashes=dashes.concat(dashes);
            path.strokeDashes=dashes;
            path.strokeDashOffset=a.dash_offset*t.scale;
        }
    }
    function pathGeometry(sub,path,t) {
        // Incremental construction avoids Illustrator merging adjacent anchors in setEntirePath.
        for (var i=0;i<sub.points.length;i++) {
            var p=path.pathPoints.add(),q=sub.points[i];
            p.anchor=mapped(q.a,t);p.leftDirection=mapped(q.l,t);p.rightDirection=mapped(q.r,t);
            p.pointType=PointType.CORNER;
        }
        path.closed=sub.closed;
        if(path.pathPoints.length!==sub.points.length) fail('ANCHOR_COUNT_MISMATCH');
    }
    function resolveFont(a) {
        var wanted=String(a.font_family).toLowerCase();
        var bold=String(a.font_weight).indexOf('bold')>=0 || parseInt(a.font_weight,10)>=600;
        var italic=a.font_style==='italic'||a.font_style==='oblique';
        var exact=null,best=null,bestScore=-1000;
        for(var i=0;i<app.textFonts.length;i++) {
            var f=app.textFonts[i];
            if(String(f.name).toLowerCase()===wanted) exact=f;
            if(exact===f && wanted.indexOf('-')>=0) return f;
            if(String(f.family).toLowerCase()!==wanted && String(f.name).toLowerCase()!==wanted) continue;
            var style=String(f.style).toLowerCase();
            var heavyFace=/bold|black|heavy|demi|semibold/.test(style);
            if(heavyFace!==bold || (style.indexOf('italic')>=0||style.indexOf('oblique')>=0)!==italic) continue;
            // Prefer the intended weight even when Black / Light faces enumerate first.
            var score=bold?(/\bbold\b/.test(style)?30:(/demi|semibold/.test(style)?10:0)):(/regular|normal|roman|book/.test(style)?30:(/light|thin/.test(style)?-10:10));
            if(score>bestScore){best=f;bestScore=score;}
            if(score===30) return f;
        }
        // Exact PostScript font names explicitly select a face; do not substitute a different family.
        if(exact!==null && wanted.indexOf('-')>=0) return exact;
        if(best!==null) return best;
        fail('FONT_NOT_FOUND: '+a.font_family+' / '+a.font_weight+' / '+a.font_style);
    }
    function createAtom(a,parent,doc,t) {
        var created=null;
        if(a.kind==='text') {
            var font=resolveFont(a);
            var point=mapped(a.position,t);
            created=doc.textFrames.pointText([0,0]);
            try {
                created.contents=a.text;
                var range=created.textRange;
                range.characterAttributes.textFont=font;
                range.characterAttributes.size=a.font_size*t.scale;
                if(a.fill!==null) range.characterAttributes.fillColor=rgb(a.fill);
                range.characterAttributes.tracking=Math.round(a.letter_spacing/a.font_size*1000);
                range.paragraphAttributes.justification=a.anchor==='middle'?Justification.CENTER:(a.anchor==='end'?Justification.RIGHT:Justification.LEFT);
                if(a.rotation) created.rotate(-a.rotation,true,true,true,true,Transformation.DOCUMENTORIGIN);
                created.translate(point[0],point[1]);
                created.move(parent,ElementPlacement.PLACEATEND);
            } catch(error) {try{created.remove();}catch(ignore){} throw error;}
        } else if(a.kind==='path') {
            if(a.subpaths.length===1) {
                created=parent.pathItems.add(); pathGeometry(a.subpaths[0],created,t);paint(a,created,t);
            } else {
                created=parent.compoundPathItems.add();
                for(var i=0;i<a.subpaths.length;i++) {
                    var child=created.pathItems.add();pathGeometry(a.subpaths[i],child,t);paint(a,child,t);
                }
            }
        } else fail('UNSUPPORTED_ATOM');
        created.name=a.name;created.opacity=a.opacity;
        created.zOrder(ZOrderMethod.BRINGTOFRONT);
        return created;
    }
    function ownItem(container,wanted) {
        for(var i=0;i<container.pageItems.length;i++) {
            var x=container.pageItems[i];
            if(x.name===wanted && x.parent===container) return x;
        }
        return null;
    }
    function verifyBatch(g,atoms) {
        if(String(g.note)!=='complete|'+c.cacheHash+'|'+atoms.length) fail('BATCH_PROVENANCE_MISMATCH');
        var topCount=0;
        for(var z=0;z<g.pageItems.length;z++) if(g.pageItems[z].parent===g) topCount++;
        if(topCount!==atoms.length) fail('COMPLETED_BATCH_CHANGED');
        for(var i=0;i<atoms.length;i++) {
            var item=ownItem(g,atoms[i].name);
            if(item===null) fail('COMPLETED_OBJECT_MISSING: '+atoms[i].name);
            if(atoms[i].kind==='text' && item.typename!=='TextFrame') fail('TEXT_NO_LONGER_LIVE');
        }
    }
    var doc=null,previousLayer=null;
    try {
        if(!/^[0-9a-f]{64}$/.test(c.cacheHash)) fail('BAD_CACHE_HASH');
        if(!/^svl_[0-9a-f]{24}$/.test(c.rootName)) fail('BAD_ROOT_NAME');
        doc=findDoc();previousLayer=doc.activeLayer;
        var root=rootOf(doc),t;
        if(c.operation==='begin') {
            if(root!==null) {parseRoot(root);return 'OK|RESUMED';}
            if(!validNumber(c.maxWidthFraction)||!validNumber(c.maxHeightFraction)||c.maxWidthFraction<=0||c.maxWidthFraction>1||c.maxHeightFraction<=0||c.maxHeightFraction>1) fail('BAD_SIZE_FRACTION');
            // Resolve every font before creating any artwork.
            for(var fi=0;fi<c.fontAtoms.length;fi++) resolveFont(c.fontAtoms[fi]);
            t=choosePlacement(doc);
            var layer=doc.layers.add();layer.name='Scientific vector '+c.rootName.substring(4);
            root=layer.groupItems.add();root.name=c.rootName;
            root.note='scientific-vector-local|'+c.cacheHash+'|'+t.left+'|'+t.top+'|'+t.scale;
            return 'OK|CREATED';
        }
        if(root===null) fail('ROOT_GROUP_MISSING');
        t=parseRoot(root);
        if(c.operation==='batch') {
            if(!/^batch_\d{5}$/.test(c.batchName)) fail('BAD_BATCH_NAME');
            var container=batchParent(doc,root,c.atoms,true);
            var batch=group(container,c.batchName);
            if(batch!==null) {
                if(String(batch.note).indexOf('complete|')===0) {verifyBatch(batch,c.atoms);return 'OK|SKIP';}
                // Only an incomplete batch created by this exact job can be removed.
                if(batch.note!=='pending|'+c.cacheHash) fail('UNOWNED_BATCH_COLLISION');
                batch.remove();
            }
            batch=container.groupItems.add();batch.name=c.batchName;batch.note='pending|'+c.cacheHash;
            try {
                for(var ai=0;ai<c.atoms.length;ai++) createAtom(c.atoms[ai],batch,doc,t);
                batch.note='complete|'+c.cacheHash+'|'+c.atoms.length;
                batch.zOrder(ZOrderMethod.BRINGTOFRONT);verifyBatch(batch,c.atoms);
                return 'OK|DRAWN|objects='+c.atoms.length;
            } catch(error) {try{batch.remove();}catch(ignoreRemove){}throw error;}
        }
        if(c.operation==='verify') {
            for(var bi=0;bi<c.batches.length;bi++) {
                var bg=group(batchParent(doc,root,c.batches[bi].atoms,false),c.batches[bi].name);
                if(bg===null) fail('BATCH_MISSING');
                verifyBatch(bg,c.batches[bi].atoms);
            }
            if(root.rasterItems.length || root.placedItems.length) fail('RASTER_CONTAMINATION');
            var textRoot=rootOf(doc,c.rootName+'_text');
            if(textRoot && (textRoot.rasterItems.length||textRoot.placedItems.length)) fail('RASTER_CONTAMINATION');
            return 'OK|VERIFIED';
        }
        if(c.operation==='audit') {
            var roots=[root],textRoot=rootOf(doc,c.rootName+'_text'),textCount=0,fonts=[],names={};
            if(textRoot) roots.push(textRoot);
            function visit(container) {
                for(var pi=0;pi<container.pageItems.length;pi++) {
                    var it=container.pageItems[pi];
                    if(it.parent!==container) continue;
                    if(it.typename==='RasterItem'||it.typename==='PlacedItem') fail('RASTER_CONTAMINATION');
                    if(it.typename==='GroupItem') visit(it);
                    if(it.typename==='TextFrame') {
                        textCount++;var fn=String(it.textRange.characterAttributes.textFont.name);
                        if(!names[fn]) {names[fn]=true;fonts.push(fn);}
                    }
                }
            }
            for(var ri=0;ri<roots.length;ri++) visit(roots[ri]);
            return 'OK|AUDIT|live_text='+textCount+'|fonts='+fonts.join(',')+'|separate_text_layer='+!!textRoot;
        }
        if(c.operation==='save') {
            var target=new File(c.outputAi);
            try {
                if(samePath(doc.fullName.fsName,target.fsName) && !c.resumeOutput) fail('REFUSE_ORIGINAL_FILE_OVERWRITE');
            } catch(nameError) {if(String(nameError).indexOf('REFUSE_')>=0) throw nameError;}
            var opt=new IllustratorSaveOptions();opt.pdfCompatible=true;opt.compressed=true;
            doc.saveAs(target,opt);
            return 'OK|SAVED|documentName='+doc.name;
        }
        if(c.operation==='export') {
            app.redraw();
            var png=new ExportOptionsPNG24();png.transparency=false;png.artBoardClipping=true;
            png.horizontalScale=200;png.verticalScale=200;png.antiAliasing=true;
            doc.exportFile(new File(c.outputPng),ExportType.PNG24,png);
            return 'OK|EXPORTED';
        }
        fail('UNKNOWN_OPERATION');
    } catch(error) {
        return 'ERROR|'+String(error).replace(/[\r\n]/g,' ');
    } finally {
        if(doc!==null && previousLayer!==null) {try{doc.activeLayer=previousLayer;}catch(ignoreLayer){}}
    }
}());
