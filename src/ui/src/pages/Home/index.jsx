import React, { useState, useEffect } from "react";
import styles from "./Home.module.scss";
import { Button, Dialog, DialogContent, IconButton, Box } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useNavigate } from "react-router-dom";
import { CAROUSEL_IMAGES } from "../../utilis/constants";
import Navbar from "../../components/Navbar";

const Home = () => {
  const navigate = useNavigate();

  const [isVideoOpen, setIsVideoOpen] = useState(false);
  const [currentImage, setCurrentImage] = useState(0);
  const [fade, setFade] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setFade(true);
      setTimeout(() => {
        setCurrentImage((prev) => (prev + 1) % CAROUSEL_IMAGES.length);
        setFade(false);
      }, 500);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Navbar variant="landing" />

      <div className={styles.homeContainer}>
        <div className={styles.contentWrapper}>
          <div className={styles.leftSection}>
            <h1>KinFin Analysis</h1>
            <p>
              Interactive exploration of gene homology across taxa, bringing
              protein clustering insights to your browser.
            </p>
            <div className={styles.buttonGroup}>
              <Button
                variant="outlined"
                color="primary"
                onClick={() => setIsVideoOpen(true)}
                sx={{ padding: "10px 20px" }}
              >
                View Demo
              </Button>
              <Button
                variant="contained"
                color="primary"
                onClick={() => {
                  navigate("/define-node-labels");
                }}
                sx={{ padding: "10px 20px" }}
              >
                Start Analysis
              </Button>
            </div>
          </div>

          <div className={styles.rightSection}>
            <img
              src={CAROUSEL_IMAGES[currentImage]}
              alt={`KinFin slide ${currentImage + 1}`}
              className={`${styles.carouselImage} ${
                fade ? styles.fadeOut : ""
              }`}
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = "/images/fallback.png";
              }}
            />
          </div>
        </div>

        <Dialog
          open={isVideoOpen}
          onClose={() => setIsVideoOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogContent sx={{ position: "relative", padding: 0 }}>
            <IconButton
              onClick={() => setIsVideoOpen(false)}
              sx={{
                position: "absolute",
                right: 8,
                top: 8,
                zIndex: 1,
                color: "#fff",
                backgroundColor: "rgba(0,0,0,0.5)",
                "&:hover": { backgroundColor: "rgba(0,0,0,0.7)" },
              }}
            >
              <CloseIcon />
            </IconButton>

            <div className={styles.videoWrapper}>
              <iframe
                src="https://www.youtube.com/embed/n-Jghkfi5fQ?si=-2VrDNf32AhtOvOW"
                title="KinFin Demo Video"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </Box>
  );
};

export default Home;
