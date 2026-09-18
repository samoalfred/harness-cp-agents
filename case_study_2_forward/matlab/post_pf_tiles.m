%% Individual post-deformation pole-figure tiles (paper order/scale)
% Saves one tight PNG per {hkl} for {111},{100},{110}, upper hemisphere,
% fixed colour range [0 3.5], no colorbar -- for a clean aligned comparison
% against the reference (paper Fig. 2c).
%
% Outputs: matlab/figures/tile_mine_111.png , _100.png , _110.png

clear; close all;
% Initialize MTEX. Set the MTEX_ROOT environment variable to your MTEX
% installation directory (the folder containing startup_mtex.m), or edit the
% fallback path below.
mtex_root = getenv('MTEX_ROOT');
if isempty(mtex_root)
    mtex_root = fullfile(getenv('USERPROFILE'), 'OneDrive - Umich', ...
        'Documents', 'MATLAB', 'mtex-6.0.0', 'mtex-6.0.0');
end
run(fullfile(mtex_root, 'startup_mtex.m'));

script_dir = fileparts(mfilename('fullpath'));
fig_dir    = fullfile(script_dir, 'figures');
if ~exist(fig_dir,'dir'), mkdir(fig_dir); end

cs = crystalSymmetry('m-3m');
ss = specimenSymmetry('triclinic');
setMTEXpref('xAxisDirection','east');
setMTEXpref('zAxisDirection','outOfPlane');

r = dlmread(fullfile(script_dir,'orientations_post_deformation.csv'), ',');
r = r(:,1:3);
mags = sqrt(sum(r.^2,2));
v    = vector3d(r(:,1)./mags, r(:,2)./mags, r(:,3)./mags);
ori  = orientation('axis', v, 'angle', 2*atan(mags), cs, ss);
odf  = calcDensity(ori, 'halfwidth', 8*degree);

hkl   = {Miller(1,1,1,cs), Miller(1,0,0,cs), Miller(1,1,0,cs)};
names = {'111','100','110'};

for k = 1:3
    figure('Visible','off','Position',[100 100 460 460],'Color','w');
    plotPDF(odf, hkl{k}, 'smooth', 'resolution', 2*degree, 'upper');
    setColorRange([0 3.5]);
    out = fullfile(fig_dir, ['tile_mine_' names{k} '.png']);
    print(gcf, out, '-dpng', '-r150');
    close(gcf);
    fprintf('Saved %s\n', out);
end
