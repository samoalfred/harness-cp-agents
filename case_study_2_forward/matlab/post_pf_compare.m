%% Post-deformation pole figures: 100 vs 1000 Taylor substeps, paper scale
% Renders {111},{100},{110} upper-hemisphere pole figures at fixed [0,3.5] MRD
% for both the 100- and 1000-substep runs, for a like-for-like comparison.
%
% Outputs: matlab/figures/post_pf_100sub.png , post_pf_1000sub.png

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
h = [Miller(1,1,1,cs), Miller(1,0,0,cs), Miller(1,1,0,cs)];

files  = {'orientations_post_deformation_100sub.csv', 'orientations_post_deformation_1000sub.csv'};
labels = {'100sub', '1000sub'};

for k = 1:2
    r = dlmread(fullfile(script_dir, files{k}), ',');
    r = r(:,1:3);
    mags = sqrt(sum(r.^2,2));
    v    = vector3d(r(:,1)./mags, r(:,2)./mags, r(:,3)./mags);
    ori  = orientation('axis', v, 'angle', 2*atan(mags), cs, ss);
    odf  = calcDensity(ori, 'halfwidth', 8*degree);

    figure('Visible','off','Position',[100 100 1250 430]);
    plotPDF(odf, h, 'smooth', 'resolution', 2*degree, 'upper');
    setColorRange([0 3.5]);
    mtexColorbar;
    set(gcf,'Color','w');
    out = fullfile(fig_dir, ['post_pf_' labels{k} '.png']);
    print(gcf, out, '-dpng', '-r200');
    close(gcf);
    fprintf('Saved %s  (%d orientations)\n', out, length(ori));
end
