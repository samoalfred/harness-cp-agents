%% Re-plot post-deformation pole figures on the Fig.10 scale (jet, 0..2.5 MRD)
% Reads the saved post-deformation orientations from Case Study 2 and renders
% {100},{110},{111} pole figures as clean disks (no colorbar/title) so they can
% be composed side by side with Fig. 10 under one shared scale bar.
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
outdir = fullfile(script_dir, 'figures', 'cmp25');
if ~exist(outdir,'dir'), mkdir(outdir); end

cs = crystalSymmetry('m-3m');
ss = specimenSymmetry('triclinic');
setMTEXpref('xAxisDirection','east');
setMTEXpref('zAxisDirection','outOfPlane');

post_file = fullfile(script_dir, 'orientations_post_deformation.csv');
d = dlmread(post_file, ','); d = d(:,1:3);
mags = sqrt(sum(d.^2,2)); angs = 2*atan(mags); vecs = d ./ mags;
v = vector3d(vecs(:,1), vecs(:,2), vecs(:,3));
ori = orientation('axis', v, 'angle', angs, cs, ss);
odf = calcDensity(ori, 'halfwidth', 8*degree);   % same kernel as the run

hkl   = {Miller(1,0,0,cs), Miller(0,1,1,cs), Miller(1,1,1,cs)};
names = {'100','110','111'};
for i = 1:3
    pf = calcPoleFigure(odf, hkl{i}, 'resolution', 2*degree, 'complete');
    f = figure('Visible','off','Color','w');
    plot(pf, 'smooth', 'colorrange', [0 2.5]);
    colormap(jet(256));
    set(gca, 'CLim', [0 2.5]);
    cb = findobj(f, 'Type', 'Colorbar'); if ~isempty(cb), delete(cb); end
    title('');
    print(f, fullfile(outdir, ['post25_' names{i} '.png']), '-dpng', '-r150');
    close(f);
    fprintf('saved post25_%s.png  max MRD = %.2f\n', names{i}, max(pf.intensities(:)));
end
disp('DONE_COMPARE_PF');
