%% Quantitative pole-figure features for the post-deformation texture (MTEX)
% Peak intensity, central (Z) intensity, and an azimuthal-asymmetry index
% for {100},{110},{111}. All in MRD on the same ODF (halfwidth 8 deg).
clear; close all;
run('C:\Users\samoa\OneDrive - Umich\Documents\MATLAB\mtex-6.0.0\mtex-6.0.0\startup_mtex.m');
script_dir = fileparts(mfilename('fullpath'));
cs = crystalSymmetry('m-3m'); ss = specimenSymmetry('triclinic');
setMTEXpref('xAxisDirection','east'); setMTEXpref('zAxisDirection','outOfPlane');

post_file = fullfile(script_dir, 'orientations_post_deformation.csv');
qd = dlmread(post_file, ','); qd = qd(:,1:3);
qm = sqrt(sum(qd.^2,2)); qa = 2*atan(qm); qv = qd ./ qm;
ori = orientation('axis', vector3d(qv(:,1),qv(:,2),qv(:,3)), 'angle', qa, cs, ss);
odf = calcDensity(ori, 'halfwidth', 8*degree);

hkl = {Miller(1,0,0,cs), Miller(0,1,1,cs), Miller(1,1,1,cs)};
names = {'100','110','111'};
fprintf('==FEATURES== %s\n', script_dir);
for i = 1:3
    pf = calcPoleFigure(odf, hkl{i}, 'resolution', 2*degree, 'complete');
    I  = pf.intensities(:);
    r  = pf.r; th = r.theta(:);      % polar angle from Z (radians)
    Imax = max(I);
    Ic   = mean(I(th < 5*degree));   % central pole density (along Z)
    % azimuthal-asymmetry index: mean over polar rings of CV(intensity vs azimuth)
    edges = (5:5:85)*degree; cvs = [];
    for k = 1:numel(edges)-1
        m = th>=edges(k) & th<edges(k+1);
        if sum(m) > 8, cvs(end+1) = std(I(m))/mean(I(m)); end %#ok<AGROW>
    end
    Asym = mean(cvs);
    fprintf('PF_%s Imax=%.3f Icentral=%.3f AzimCV=%.4f\n', names{i}, Imax, Ic, Asym);
end
fprintf('TextureIndex=%.4f\n', textureindex(odf));
disp('DONE_FEATURES');
