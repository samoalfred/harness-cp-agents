%% Render pre- and post-deformation pole-figure tiles (paper order/scale)
% For a clean before/after SI figure: one tight PNG per {hkl} for {111},{100},
% {110}, upper hemisphere, fixed [0 3.5] MRD, no colorbar.
% Pre  : ../orientations.txt              (initial grain orientations, Rodrigues)
% Post : orientations_post_deformation.csv (deformed quadrature orientations)
% Output: figures/tile_pre_{hkl}.png , figures/tile_post_{hkl}.png

clear; close all;
run('C:\Users\samoa\OneDrive - Umich\Documents\MATLAB\mtex-6.0.0\mtex-6.0.0\startup_mtex.m');

sd = fileparts(mfilename('fullpath'));
fig_dir = fullfile(sd,'figures');
if ~exist(fig_dir,'dir'), mkdir(fig_dir); end
cs = crystalSymmetry('m-3m');
ss = specimenSymmetry('triclinic');
setMTEXpref('xAxisDirection','east'); setMTEXpref('zAxisDirection','outOfPlane');
hkl = {Miller(1,1,1,cs),'111'; Miller(1,0,0,cs),'100'; Miller(1,1,0,cs),'110'};

% Load pre (initial) and post (deformed) orientations
pre = dlmread(fullfile(sd,'..','orientations.txt'), '\t', 1, 0); pre = pre(:,2:4);
post = dlmread(fullfile(sd,'orientations_post_deformation.csv'), ','); post = post(:,1:3);

sets = {pre,'pre'; post,'post'};
for s = 1:2
    r = sets{s,1}; prefix = sets{s,2};
    m = sqrt(sum(r.^2,2));
    o = orientation('axis', vector3d(r(:,1)./m, r(:,2)./m, r(:,3)./m), ...
                    'angle', 2*atan(m), cs, ss);
    odf = calcDensity(o, 'halfwidth', 8*degree);
    for k = 1:3
        figure('Visible','off','Position',[100 100 460 460],'Color','w');
        plotPDF(odf, hkl{k,1}, 'smooth', 'resolution', 2*degree, 'upper');
        setColorRange([0 3.5]);
        print(gcf, fullfile(fig_dir, ['tile_' prefix '_' hkl{k,2} '.png']), '-dpng', '-r150');
        close(gcf);
    end
    fprintf('rendered %s tiles\n', prefix);
end
disp('done');
