%% Pole Figure Generator — Pre and Post Deformation (Matched Color Scales)
% Computes ODFs for both pre- and post-deformation orientations.
% For each {hkl}, the color range is matched between pre and post so that
% the comparison is quantitatively meaningful.
%
% Pre-deformation : reads orientations.txt (grain-level Rodrigues vectors)
% Post-deformation: reads orientations_post_deformation.csv (quadrature points)
%
% Output:
%   matlab/figures/pre_pf{100,110,111}.png       (overwrites microstructure_gen outputs)
%   matlab/figures/post_deformation/post_pf{100,110,111}.png
%
% Source: oriplot_big.m (Juyoung Jeong / Veera Sundararaghavan, U-Michigan)
% Modified for SS316L_Pipeline — matched colorscale, publication quality.

clear; close all;

% Initialize MTEX
% Initialize MTEX. Set the MTEX_ROOT environment variable to your MTEX
% installation directory (the folder containing startup_mtex.m), or edit the
% fallback path below.
mtex_root = getenv('MTEX_ROOT');
if isempty(mtex_root)
    mtex_root = fullfile(getenv('USERPROFILE'), 'OneDrive - Umich', ...
        'Documents', 'MATLAB', 'mtex-6.0.0', 'mtex-6.0.0');
end
run(fullfile(mtex_root, 'startup_mtex.m'));

% Paths
script_dir   = fileparts(mfilename('fullpath'));
fig_dir_pre  = fullfile(script_dir, 'figures');
fig_dir_post = fullfile(script_dir, 'figures', 'post_deformation');
if ~exist(fig_dir_pre,  'dir'), mkdir(fig_dir_pre);  end
if ~exist(fig_dir_post, 'dir'), mkdir(fig_dir_post); end

%% Crystal symmetry (FCC)
cs = crystalSymmetry('m-3m');
ss = specimenSymmetry('triclinic');

%% Plotting convention
setMTEXpref('xAxisDirection', 'east');
setMTEXpref('zAxisDirection', 'outOfPlane');

% =========================================================================
%% Load PRE-deformation orientations from orientations.txt
% =========================================================================
pre_file = fullfile(script_dir, '..', 'orientations.txt');
fprintf('Reading pre-deformation: %s\n', pre_file);
pre_raw  = dlmread(pre_file, '\t', 1, 0);   % skip 1 header line, tab-delimited
pre_dats = pre_raw(:, 2:4);                 % cols 2,3,4 = rx, ry, rz

pre_mags = sqrt(sum(pre_dats.^2, 2));
pre_angs = 2 * atan(pre_mags);
pre_vecs = pre_dats ./ pre_mags;
pre_v    = vector3d(pre_vecs(:,1), pre_vecs(:,2), pre_vecs(:,3));
pre_ori  = orientation('axis', pre_v, 'angle', pre_angs, cs, ss);
fprintf('Pre-deformation: %d grain orientations\n', length(pre_ori));

fprintf('Calculating pre-deformation ODF...\n');
pre_odf = calcDensity(pre_ori, 'halfwidth', 8*degree);

% =========================================================================
%% Load POST-deformation orientations
% =========================================================================
post_file = fullfile(script_dir, 'orientations_post_deformation.csv');
fprintf('Reading post-deformation: %s\n', post_file);
post_dats = dlmread(post_file, ',');
post_dats = post_dats(:, 1:3);   % rx, ry, rz

post_mags = sqrt(sum(post_dats.^2, 2));
post_angs = 2 * atan(post_mags);
post_vecs = post_dats ./ post_mags;
post_v    = vector3d(post_vecs(:,1), post_vecs(:,2), post_vecs(:,3));
post_ori  = orientation('axis', post_v, 'angle', post_angs, cs, ss);
fprintf('Post-deformation: %d quadrature points\n', length(post_ori));

fprintf('Calculating post-deformation ODF...\n');
post_odf = calcDensity(post_ori, 'halfwidth', 8*degree);

% =========================================================================
%% Generate matched pole figures for each {hkl}
% =========================================================================
hkl_list   = {Miller(1,0,0,cs), Miller(0,1,1,cs), Miller(1,1,1,cs)};
hkl_names  = {'100', '110', '111'};
hkl_titles = {'(100)', '(110)', '(111)'};   % parentheses avoid TeX interpreter issues

fprintf('\nGenerating pole figures with matched color scales...\n');

for i = 1:3
    h = hkl_list{i};

    % Compute pole figures to determine intensity ranges
    pre_pf  = calcPoleFigure(pre_odf,  h, 'resolution', 2*degree, 'complete');
    post_pf = calcPoleFigure(post_odf, h, 'resolution', 2*degree, 'complete');

    pre_max  = max(pre_pf.intensities(:));
    post_max = max(post_pf.intensities(:));
    % Fixed colour range for ALL pole figures (pre/post, every {hkl}), matching
    % the paper's Fig. 2c scale (0-3.5 MRD) so every figure is directly
    % comparable and on the same scale as Reference_Plot_figures.png.
    crange   = [0, 3.5];

    fprintf('  %s: pre_max=%.2f  post_max=%.2f  fixed_range=[0, 3.5]\n', ...
        hkl_titles{i}, pre_max, post_max);

    % --- PRE figure ---
    fig_pre = figure('Visible', 'off'); clf;
    plot(pre_pf, 'smooth', 'colorrange', crange);
    cb = colorbar;
    cb.Label.String = 'MRD';
    cb.Label.FontSize = 11;
    title([hkl_titles{i}, ' Pole Figure  |  Pre-Deformation'], ...
          'FontSize', 13, 'FontWeight', 'bold', 'Interpreter', 'none');
    pre_fname = fullfile(fig_dir_pre, ['pre_pf', hkl_names{i}, '.png']);
    saveas(fig_pre, pre_fname);
    close(fig_pre);
    fprintf('  Saved pre_pf%s.png\n', hkl_names{i});

    % --- POST figure ---
    fig_post = figure('Visible', 'off'); clf;
    plot(post_pf, 'smooth', 'colorrange', crange);
    cb = colorbar;
    cb.Label.String = 'MRD';
    cb.Label.FontSize = 11;
    title([hkl_titles{i}, ' Pole Figure  |  Post-Deformation'], ...
          'FontSize', 13, 'FontWeight', 'bold', 'Interpreter', 'none');
    post_fname = fullfile(fig_dir_post, ['post_pf', hkl_names{i}, '.png']);
    saveas(fig_post, post_fname);
    close(fig_post);
    fprintf('  Saved post_pf%s.png\n', hkl_names{i});
end

fprintf('\nAll pole figures saved with matched color ranges.\n');
fprintf('Pre  : %s\n', fig_dir_pre);
fprintf('Post : %s\n', fig_dir_post);

% =========================================================================
%% Individual post-deformation tiles for the paper-comparison figure
% One tight PNG per {hkl} in paper column order {111},{100},{110}, upper
% hemisphere, fixed [0 3.5] MRD, no colorbar -- consumed by
% tools/texture_vs_paper.py to build the aligned this-study-vs-paper figure.
% =========================================================================
tile_hkl   = {Miller(1,1,1,cs), Miller(1,0,0,cs), Miller(1,1,0,cs)};
tile_names = {'111', '100', '110'};
for i = 1:3
    fig_t = figure('Visible','off','Position',[100 100 460 460],'Color','w');
    plotPDF(post_odf, tile_hkl{i}, 'smooth', 'resolution', 2*degree, 'upper');
    setColorRange([0 3.5]);
    % remove MTEX axis-direction glyphs (X/Y/Z) and any (hkl) label so the tile
    % is just the bare pole-figure disk for the paper-comparison figure
    delete(findall(fig_t, 'Type', 'text'));
    tile_fname = fullfile(fig_dir_pre, ['tile_mine_' tile_names{i} '.png']);
    print(fig_t, tile_fname, '-dpng', '-r150');
    close(fig_t);
    fprintf('  Saved tile_mine_%s.png\n', tile_names{i});
end

% Individual PRE-deformation (recovered initial texture) tiles, same style,
% for the supplementary three-row figure (initial -> deformed -> reference).
for i = 1:3
    fig_i = figure('Visible','off','Position',[100 100 460 460],'Color','w');
    plotPDF(pre_odf, tile_hkl{i}, 'smooth', 'resolution', 2*degree, 'upper');
    setColorRange([0 3.5]);
    delete(findall(fig_i, 'Type', 'text'));
    tile_fname = fullfile(fig_dir_pre, ['tile_init_' tile_names{i} '.png']);
    print(fig_i, tile_fname, '-dpng', '-r150');
    close(fig_i);
    fprintf('  Saved tile_init_%s.png\n', tile_names{i});
end
