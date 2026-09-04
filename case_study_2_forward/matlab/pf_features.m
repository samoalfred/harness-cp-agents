%% Pole-figure feature extraction for the post-deformation texture
clear; close all;
run('C:\Users\samoa\OneDrive - Umich\Documents\MATLAB\mtex-6.0.0\mtex-6.0.0\startup_mtex.m');
sd = fileparts(mfilename('fullpath'));
r = dlmread(fullfile(sd,'orientations_post_deformation.csv'), ',');
r = r(:,1:3);
mags = sqrt(sum(r.^2,2));
o = orientation('axis', vector3d(r(:,1)./mags, r(:,2)./mags, r(:,3)./mags), ...
                'angle', 2*atan(mags), crystalSymmetry('m-3m'), specimenSymmetry('triclinic'));
cs = crystalSymmetry('m-3m');
odf = calcDensity(o, 'halfwidth', 8*degree);
setMTEXpref('xAxisDirection','east'); setMTEXpref('zAxisDirection','outOfPlane');
hkls = {Miller(1,0,0,cs),'100'; Miller(1,1,0,cs),'110'; Miller(1,1,1,cs),'111'};
Z = vector3d.Z;
for i=1:3
  h = hkls{i,1};
  pf = calcPoleFigure(odf, h, 'resolution', 2*degree, 'complete');
  pk = max(pf.intensities(:));
  cen = odf.calcPDF(h, Z);            % pole density along Z (centre)
  fprintf('{%s}: peak=%.2f  central(Z)=%.2f\n', hkls{i,2}, pk, cen);
end
