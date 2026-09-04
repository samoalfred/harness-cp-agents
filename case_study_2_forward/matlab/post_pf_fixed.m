%% Post-deformation pole figures on the PAPER's fixed scale (0-3.5 MRD)
% Renders the {111},{100},{110} post-deformation pole figures (paper Fig. 2c
% column order) with a single shared colour range [0, 3.5], to overlay
% against Yaghoobi et al. (2022) Fig. 2c at identical scale.
%
% Output: matlab/figures/post_pf_paperscale.png

clear; close all;
run('C:\Users\samoa\OneDrive - Umich\Documents\MATLAB\mtex-6.0.0\mtex-6.0.0\startup_mtex.m');

script_dir = fileparts(mfilename('fullpath'));
fig_dir    = fullfile(script_dir, 'figures');
if ~exist(fig_dir,'dir'), mkdir(fig_dir); end

cs = crystalSymmetry('m-3m');
ss = specimenSymmetry('triclinic');
setMTEXpref('xAxisDirection','east');
setMTEXpref('zAxisDirection','outOfPlane');

% Load post-deformation orientations (Rodrigues rx,ry,rz)
post_file = fullfile(script_dir, 'orientations_post_deformation.csv');
r = dlmread(post_file, ',');
r = r(:,1:3);
mags = sqrt(sum(r.^2,2));
angs = 2*atan(mags);
vecs = r ./ mags;
v    = vector3d(vecs(:,1), vecs(:,2), vecs(:,3));
ori  = orientation('axis', v, 'angle', angs, cs, ss);
fprintf('Post-deformation: %d orientations\n', length(ori));

odf = calcDensity(ori, 'halfwidth', 8*degree);

% Paper Fig. 2c column order and fixed scale
h = [Miller(1,1,1,cs), Miller(1,0,0,cs), Miller(1,1,0,cs)];

figure('Visible','off','Position',[100 100 1250 430]);
plotPDF(odf, h, 'smooth', 'resolution', 2*degree, 'upper');
setColorRange([0 3.5]);
mtexColorbar;
set(gcf,'Color','w');

out = fullfile(fig_dir, 'post_pf_paperscale.png');
print(gcf, out, '-dpng', '-r200');
fprintf('Saved %s\n', out);
