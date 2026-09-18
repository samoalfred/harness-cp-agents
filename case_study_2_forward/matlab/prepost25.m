%% Re-plot PRE and POST deformation pole figures on the Fig.10 scale (jet, 0..2.5 MRD)
% Clean disks (no colorbar/title) so they compose under one shared 0-2.5 scale bar.
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

% PRE-deformation orientations (grain-level Rodrigues, tab-delimited, 1 header line)
pre_file = fullfile(script_dir, '..', 'orientations.txt');
pre_raw  = dlmread(pre_file, '\t', 1, 0);
pd = pre_raw(:, 2:4);
pm = sqrt(sum(pd.^2,2)); pa = 2*atan(pm); pv = pd ./ pm;
pre_ori = orientation('axis', vector3d(pv(:,1),pv(:,2),pv(:,3)), 'angle', pa, cs, ss);
pre_odf = calcDensity(pre_ori, 'halfwidth', 8*degree);
fprintf('PRE: %d orientations\n', length(pre_ori));

% POST-deformation orientations (quadrature Rodrigues, comma-delimited)
post_file = fullfile(script_dir, 'orientations_post_deformation.csv');
qd = dlmread(post_file, ','); qd = qd(:,1:3);
qm = sqrt(sum(qd.^2,2)); qa = 2*atan(qm); qv = qd ./ qm;
post_ori = orientation('axis', vector3d(qv(:,1),qv(:,2),qv(:,3)), 'angle', qa, cs, ss);
post_odf = calcDensity(post_ori, 'halfwidth', 8*degree);
fprintf('POST: %d orientations\n', length(post_ori));

hkl   = {Miller(1,0,0,cs), Miller(0,1,1,cs), Miller(1,1,1,cs)};
names = {'100','110','111'};
stages = {'pre','post'};
for s = 1:2
    if s==1, odf = pre_odf; else, odf = post_odf; end
    for i = 1:3
        pf = calcPoleFigure(odf, hkl{i}, 'resolution', 2*degree, 'complete');
        f = figure('Visible','off','Color','w');
        plot(pf, 'smooth', 'colorrange', [0 2.5]);
        colormap(jet(256)); set(gca,'CLim',[0 2.5]);
        cb = findobj(f,'Type','Colorbar'); if ~isempty(cb), delete(cb); end
        title('');
        print(f, fullfile(outdir, [stages{s} '25_' names{i} '.png']), '-dpng', '-r150');
        close(f);
        fprintf('saved %s25_%s.png  max MRD = %.2f\n', stages{s}, names{i}, max(pf.intensities(:)));
    end
end
disp('DONE_PREPOST25');
